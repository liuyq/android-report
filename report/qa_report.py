# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
import requests

from abc import abstractmethod

logger = logging.getLogger(__name__)

class DotDict(dict):
    '''dict.item notation for dict()'s'''
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


class RESTFullApi():
    def __init__(self, domain, api_token):
        self.domain = domain
        self.api_token = api_token

    def call_with_full_url(self, request_url=''):
        headers = { 
                'Content-Type': 'application/json',
                'Authorization': 'Token %s' % self.api_token
                }
        r = requests.get(request_url, headers=headers)
        ret = DotDict(r.json())
        if (not r.ok or ('error' in ret and ret.error == True)):
            raise Exception(r.url, r.reason, r.status_code, r.json())
        return ret 

    def call_with_api_url(self, api_url=''):
        full_url = '%s/%s' % (self.get_api_url_prefix().strip('/'), api_url.strip('/'))
        return self.call_with_full_url(request_url=full_url)

    @abstractmethod
    def get_api_url_prefix(sefl):
        """Return the url prefix, which we could use with the api url directly"""
        """Should never be called."""
        raise NotImplementedError('%s.get_api_url_prefix should never be called directly' % self.__class__.__name__)


class LAVAApi(RESTFullApi):
    def get_api_url_prefix(self):
        return 'https://%s/api/v0.1/' % self.domain


    def get_job(self, job_id=None):
        api_url = "/jobs/%s" % job_id
        return self.call_with_api_url(api_url=api_url)


class QAReportApi(RESTFullApi):
    def get_api_url_prefix(self):
        return 'https://%s/' % self.domain.strip('/')


    def get_projects(self):
        api_url = "/api/projects/"
        return self.call_with_api_url(api_url=api_url).get('results')


    def get_all_builds(self, project_id):
        builds_api_url = "api/projects/%s/builds" % project_id
        return self.call_with_api_url(api_url=builds_api_url).get('results')


    def get_build_with_version(self, build_version, project_id):
        for build in self.get_all_builds(project_id):
            if build.get('version') == build_version:
                return build
        return None


    def get_jobs_for_build(self, build_id):
        api_url = "api/builds/%s/testjobs" % build_id
        return self.call_with_api_url(api_url=api_url).get('results')


    def get_project_with_name(self, project_name):
        for project in self.get_projects():
            if project.get('full_name') == project_name:
                return project
        return None


    def get_builds_with_project_name(self, project_name):
        qa_report_project = self.get_project_with_name(project_name)
        if not qa_report_project:
            logger.info("qa report project for build %s not found" % project_name)
            return []
        return self.get_all_builds(qa_report_project.get('id'))


    def get_jobs_with_project_name_build_version(self, project_name, build_version):
        qa_report_project = self.get_project_with_name(project_name)
        if not qa_report_project:
            logger.info("qa report project for build %s not found" % project_name)
            return []
        build = self.get_build_with_version(build_version, qa_report_project.get('id'))
        if not build:
            logger.info("qa report build for project(%s) with build no(%s) not found" % (project_name, build_version))
            return []
        return self.get_jobs_for_build(build.get('id'))