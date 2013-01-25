# -*- coding: utf-8 -*-
#
# Copyright © 2012 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

"""
Contains content applicability management classes
"""

from pulp.server.managers import factory as managers
from pulp.server.managers.pluginwrapper import PluginWrapper
from pulp.plugins.profiler import Profiler
from pulp.plugins.model import ApplicabilityReport
from pulp.plugins.model import Consumer as ProfiledConsumer
from pulp.plugins.conduits.profiler import ProfilerConduit
from pulp.plugins.loader import api as plugin_api
from pulp.plugins.loader import exceptions as plugin_exceptions
from logging import getLogger

_LOG = getLogger(__name__)


class ApplicabilityManager(object):

    def units_applicable(self, consumer_criteria, repo_criteria=None, units=None):
        """
        Determine and report which of the specified content units
        is applicable to consumers specified by the I{consumer_criteria} 
        with repos specified by I{repo_criteria}. If units is None, all
        units in the repos bound to the consumer are considered.

        @param consumer_criteria: The consumer selection criteria.
        @type consumer_criteria: dict

        @param repo_criteria: The repo selection criteria.
        @type repo_criteria: dict

        @param units: A dictionary of type_id : list of unit keys
        @type units: dict
                {<type_id1> : [{<unit_key1>}, {<unit_key2}, ..]
                 <type_id2> : [{<unit_key1>}, {<unit_key2}, ..]}

        @return: A dict:
            {consumer_id:[<ApplicabilityReport>]}
        @rtype: dict
        """
        result = {}
        conduit = ProfilerConduit()

        # Get consumer ids satisfied by specified consumer criteria
        consumer_query_manager = managers.consumer_query_manager()
        consumer_ids = [c['id'] for c in consumer_query_manager.find_by_criteria(consumer_criteria)]

        # Make sure you can get profiles of all consumers
        profile_manager = managers.consumer_profile_manager()
        profile_manager.find_profiles(consumer_ids)

        # Get repo ids satisfied by specified consumer criteria
        if repo_criteria:
            repo_query_manager = managers.repo_query_manager()
            repo_criteria_ids = [r['id'] for r in repo_query_manager.find_by_criteria(repo_criteria)]
        else:
            repo_criteria_ids = None

        bind_manager = managers.consumer_bind_manager()
        repo_unit_association_query_manager = managers.repo_unit_association_query_manager()

        for consumer_id in consumer_ids:

            # Find repos bound to a consumer
            bindings = bind_manager.find_by_consumer(consumer_id)
            bound_repo_ids = [b['repo_id'] for b in bindings]

            # If repo_criteria is not specified, user repos bound to the consumer, else take intersections 
            # of repos specified in the criteria and repos bound to the consumer.
            if repo_criteria_ids is None:
                repo_ids = bound_repo_ids
            else:
                repo_ids = list(set(bound_repo_ids) & set(repo_criteria_ids))

            # If units are not specified, consider all units in the repos bound to the consumer.
            if units is None:
                for repo_id in repo_ids:
                    units = repo_unit_association_query_manager.get_unit_ids(repo_id)

            for typeid, unit_keys in units:
                # Find a profiler for each type id and find units applicable using that profiler.
                profiler, cfg = self.__profiler(typeid)
                pc = self.__profiled_consumer(consumer_id)
                for unit_key in unit_keys:
                    report = profiler.unit_applicable(pc, repo_ids, unit_key, cfg, conduit)
                    report.unit = unit_key
                    ulist = result.setdefault(consumer_id, [])
                    ulist.append(report)

        return result


    def __profiler(self, typeid):
        """
        Find the profiler.
        Returns the Profiler base class when not matched.
        @param typeid: The content type ID.
        @type typeid: str
        @return: (profiler, cfg)
        @rtype: tuple
        """
        try:
            plugin, cfg = plugin_api.get_profiler_by_type(typeid)
        except plugin_exceptions.PluginNotFound:
            plugin = Profiler()
            cfg = {}
        return PluginWrapper(plugin), cfg

    def __profiled_consumer(self, id):
        """
        Get a profiler consumer model object.
        @param id: A consumer ID.
        @type id: str
        @return: A populated profiler consumer model object.
        @rtype: L{ProfiledConsumer}
        """
        profiles = {}
        manager = managers.consumer_profile_manager()
        for p in manager.get_profiles(id):
            typeid = p['content_type']
            profile = p['profile']
            profiles[typeid] = profile
        return ProfiledConsumer(id, profiles)
