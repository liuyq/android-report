## https://docs.djangoproject.com/en/1.11/topics/db/managers/
## https://docs.djangoproject.com/en/dev/howto/custom-management-commands/#howto-custom-management-commands
## https://medium.com/@bencleary/django-scheduled-tasks-queues-part-1-62d6b6dc24f8
## https://medium.com/@bencleary/django-scheduled-tasks-queues-part-2-fc1fb810b81d
## https://medium.com/@kevin.michael.horan/scheduling-tasks-in-django-with-the-advanced-python-scheduler-663f17e868e6
## https://django-background-tasks.readthedocs.io/en/latest/


import datetime
import json
import logging
import os
import re
import yaml

from django.core.management.base import BaseCommand, CommandError

from django.utils.timesince import timesince

from lkft.models import KernelChange, CiBuild, ReportBuild, ReportProject, ReportJob

from lcr import qa_report
from lkft import lkft_config
from lcr.irc import IRC

from lcr.settings import QA_REPORT, QA_REPORT_DEFAULT

from lkft.views import get_kernel_changes_info, cache_qajob_to_database
from lkft.views import extract, get_lkft_bugs, get_hardware_from_pname, get_result_file_path, get_kver_with_pname_env

logger = logging.getLogger(__name__)

qa_report_def = QA_REPORT[QA_REPORT_DEFAULT]
qa_report_api = qa_report.QAReportApi(qa_report_def.get('domain'), qa_report_def.get('token'))

class Command(BaseCommand):
    help = 'Check the build and test results for kernel changes, and send report if the jobs finished'

    def add_arguments(self, parser):
        parser.add_argument('describe', type=str, nargs='?', default=None)
        parser.add_argument("--branch",
                        help="Specify the branch for changes that to be checked",
                        dest="branch",
                        default="",
                        required=False)
        parser.add_argument("--irc-report-type",
                        help="Specify which type record will be reported: ONLY_COMPLETED, ALL",
                        dest="irc_report_type",
                        default="ONLY_COMPLETED",
                        required=False)


    def classify_bugs_and_failures(self, bugs=[], failures=[]):
        bugs_reproduced = []
        bugs_not_reproduced = []
        new_failures = []

        for module_name in sorted(failures.keys()):
            failures_in_module = failures.get(module_name)
            for test_name in sorted(failures_in_module.keys()):
                failure = failures_in_module.get(test_name)

                for bug in bugs:
                    if test_name.find(module_name) >=0:
                        # vts test, module name is the same as the test name.
                        search_key = test_name
                    else:
                        search_key = '%s %s' % (module_name, test_name)

                    if bug.summary.find(search_key) >= 0:
                        bugs_reproduced.append(bug)
                        if failure.get('bugs'):
                            failure['bugs'].append(bug)
                        else:
                            failure['bugs'] = [bug]

                if failure.get('bugs') is None or len(failure.get('bugs')) == 0:
                    new_failures.append(failure)

        bugs_not_reproduced = [ bug for bug in bugs if not (bug in bugs_reproduced) ]

        return {
                'bugs_reproduced': bugs_reproduced,
                'bugs_not_reproduced': bugs_not_reproduced,
                'new_failures': new_failures,
                }


    def get_bugs_for_project(self, project_name="", cachepool={}):
        platform_name = get_hardware_from_pname(project_name)
        project_platform_key = "%s#%s" % (project_name, platform_name)
        bugs = cachepool.get(project_platform_key)
        if bugs is None:
            bugs = get_lkft_bugs(summary_keyword=project_name, platform=platform_name)
            cachepool[project_platform_key] = bugs


    def get_failures_for_build(self, project_name="", jobs=[]):
        failures = {}
        for job in jobs:
            result_file_path = get_result_file_path(job=job)
            if not result_file_path or not os.path.exists(result_file_path):
                continue

            kernel_version = get_kver_with_pname_env(prj_name=project_name, env=job.get('environment'))

            platform = job.get('environment').split('_')[0]

            metadata = {
                'job_id': job.get('job_id'),
                'qa_job_id': qa_report_api.get_qa_job_id_with_url(job_url=job.get('url')),
                'result_url': job.get('attachment_url'),
                'lava_nick': job.get('lava_config').get('nick'),
                'kernel_version': kernel_version,
                'platform': platform,
                }
            extract(result_file_path, failed_testcases_all=failures, metadata=metadata)
        return failures


    def get_bugs_and_failures_for_qabuild(self, target_qareport_build, cachepool={}):
        qa_project = target_qareport_build.get('qa_report_project')
        project_name = qa_project.get('name')
        final_jobs = target_qareport_build.get('final_jobs')
        failures = self.get_failures_for_build(project_name=project_name, jobs=final_jobs)
        bugs = self.get_bugs_for_project(project_name=project_name, cachepool=cachepool)
        classification = self.classify_bugs_and_failures(bugs=bugs, failures=failures)
        target_qareport_build['failures'] = failures
        target_qareport_build['classification'] = classification


    def handle(self, *args, **options):
        irc_report_type = options.get('irc_report_type')
        option_branch = options.get('branch')
        describe = options['describe']
        if describe is not None:
            db_kernelchanges = KernelChange.objects_needs_report.all().filter(describe=describe)
        elif option_branch:
            db_kernelchanges = KernelChange.objects_needs_report.all().filter(branch=option_branch)
        else:
            # db_kernelchanges = KernelChange.objects_needs_report.all().filter(branch="android-5.4")
            db_kernelchanges = KernelChange.objects_needs_report.all()
        kernelchanges = get_kernel_changes_info(db_kernelchanges=db_kernelchanges)
        if len(kernelchanges) == 0:
            logger.info("No kernel change report needs to be updated")
            return

        ## cache to database
        for kernel_change_report in kernelchanges:
            kernel_change = kernel_change_report.get('kernel_change')
            if kernel_change.reported and kernel_change.result == 'ALL_COMPLETED':
                # skip database update for reported and completed records
                continue
            status = kernel_change_report.get('kernel_change_status')
            trigger_build = kernel_change_report.get('trigger_build')
            # Try to cache Trigger build information to database
            logger.info("%s %s %s" % (kernel_change.branch, kernel_change.describe, status))

            trigger_dbci_build = CiBuild.objects.get_or_create(name=trigger_build.get('name'), number=trigger_build.get('number'))[0]
            if trigger_dbci_build.kernel_change is None:
                trigger_dbci_build.kernel_change = kernel_change
            trigger_dbci_build.duration = trigger_build.get('duration').total_seconds()
            trigger_dbci_build.timestamp = trigger_build.get('start_timestamp')
            trigger_dbci_build.result = trigger_build.get('status')
            trigger_dbci_build.save()

            # Try to cache CI build information to database
            jenkins_ci_builds = kernel_change_report.get('jenkins_ci_builds')
            for ci_build in jenkins_ci_builds:
                CiBuild.objects.filter(name=ci_build.get('name'),
                                     number=ci_build.get('number')
                                 ).update(duration=ci_build.get('duration').total_seconds(),
                                     timestamp=ci_build.get('start_timestamp'),
                                     result=ci_build.get('status'))

            # Try to cache kernel change result informtion to database
            finished_timestamp = kernel_change_report.get('finished_timestamp')
            start_timestamp = kernel_change_report.get('start_timestamp')
            test_numbers = kernel_change_report.get('test_numbers')

            kernel_change = kernel_change_report.get('kernel_change')
            kernel_change.reported = ((status == 'ALL_COMPLETED') or (status == 'CI_BUILDS_ALL_FAILED'))
            kernel_change.result = status
            kernel_change.timestamp = start_timestamp
            kernel_change.duration = (finished_timestamp - start_timestamp).total_seconds()
            test_numbers.setValueForDatabaseRecord(kernel_change)
            kernel_change.save()

            # Try to cache report build informtion to database
            for qareport_build in kernel_change_report.get('qa_report_builds'):
                jenkins_ci_build = qareport_build.get('ci_build')
                dbci_build = jenkins_ci_build.get('dbci_build')
                result_numbers = qareport_build.get('numbers_of_result')

                trigger_dbci_build = CiBuild.objects.get(name=trigger_build.get('name'), number=trigger_build.get('number'))

                # save qareport project to database
                qa_project, created = ReportProject.objects.get_or_create(project_id=qareport_build.get('project_id'))
                if created:
                    qa_project.group = qareport_build.get('project_group')
                    qa_project.name = qareport_build.get('project_name')
                    qa_project.slug = qareport_build.get('project_slug')
                    qa_project.save()

                # save qareport build to database
                report_build = ReportBuild.objects.get_or_create(qa_build_id=qareport_build.get('id'))[0]
                report_build.qa_project = qa_project
                report_build.version = kernel_change.describe
                report_build.kernel_change = kernel_change
                report_build.ci_build = dbci_build
                report_build.ci_trigger_build = trigger_dbci_build
                report_build.started_at = trigger_build.get('start_timestamp')
                report_build.fetched_at = qareport_build.get('last_fetched_timestamp')
                report_build.status = qareport_build.get('build_status')
                qa_report.TestNumbers.setHashValueForDatabaseRecord(report_build, result_numbers)
                report_build.save()

                final_jobs = qareport_build.get('final_jobs')
                resubmitted_or_duplicated_jobs = qareport_build.get('resubmitted_or_duplicated_jobs')

                # save qareport job to database
                for job in final_jobs + resubmitted_or_duplicated_jobs:
                    cache_qajob_to_database(job)


        # print out the reports
        print("########## REPORTS FOR KERNEL CHANGES#################")
        num_kernelchanges = len(kernelchanges)
        index = 0
        ircMsgList=[]
        ircMsgList.append("KERNEL CHANGES STATUS REPORT STARTED: %d in total" % num_kernelchanges)
        for kernel_change_report in kernelchanges:
            kernel_change = kernel_change_report.get('kernel_change')
            status = kernel_change_report.get('kernel_change_status')
            index = index + 1
            if status == "ALL_COMPLETED":
                ircMsg = "%d/%d: %s/%s %s %s, %s/%s passed, %s/%s modules done, %s/%s jobs finished" % (index, num_kernelchanges,
                                     kernel_change.branch,
                                     kernel_change.describe,
                                     kernel_change.result,
                                     timesince(kernel_change.timestamp),
                                     kernel_change.number_passed, kernel_change.number_total,
                                     kernel_change.modules_done, kernel_change.modules_total,
                                     kernel_change.jobs_finished, kernel_change.jobs_total,
                                     )
            else:
                ircMsg = "%d/%d: %s/%s %s %s" % (index, num_kernelchanges, kernel_change.branch, kernel_change.describe, kernel_change.result, timesince(kernel_change.timestamp))

            if kernel_change.jobs_finished != kernel_change.jobs_total \
                    or status == "CI_BUILDS_ALL_FAILED" \
                    or status == "CI_BUILDS_HAS_FAILED":
                ircMsg = ircMsg + ", liuyq"

            if irc_report_type == 'ALL':
                ircMsgList.append(ircMsg)
            elif irc_report_type == 'ONLY_COMPLETED' and (status == "ALL_COMPLETED" or status == "CI_BUILDS_ALL_FAILED"):
                ircMsgList.append(ircMsg)

            continue

            trigger_build = kernel_change_report.get('trigger_build')
            jenkins_ci_builds = kernel_change_report.get('jenkins_ci_builds')
            qa_report_builds = kernel_change_report.get('qa_report_builds')
            trigger_starttimestamp = trigger_build['start_timestamp']
            finished_timestamp = kernel_change_report.get('finished_timestamp')

            print("\t Reports for CI Builds:")
            for build in jenkins_ci_builds:
                dbci_build = build.get('dbci_build')
                if build.get('status') == 'INPROGRESS':
                    print("\t\t %s#%s %s, started at %s, %s ago" % (dbci_build.name, dbci_build.number,
                                                             build.get('status'),
                                                             build.get('start_timestamp'),
                                                             timesince(build.get('start_timestamp'))))
                else:
                    print("\t\t %s#%s %s, started at %s, %s ago, took %s" % (dbci_build.name, dbci_build.number,
                                                             build.get('status'),
                                                             build.get('start_timestamp'),
                                                             timesince(build.get('start_timestamp')),
                                                             build.get('duration')))

            queued_ci_builds = kernel_change_report.get('queued_ci_builds')
            for build in  queued_ci_builds:
                inqueuesince = datetime.datetime.fromtimestamp(int(build.get('inQueueSince')/1000), tz=timezone.utc)
                #duration = datetime_now - inqueuesince
                print("\t\t %s: still in queue since %s ago" % (build.get('build_name'), timesince(inqueuesince)))

            not_reported_ci_builds = kernel_change_report.get('not_reported_ci_builds')
            for build in not_reported_ci_builds:
                print("\t\t %s: not reported" % (str(build)))

            disabled_ci_builds = kernel_change_report.get('disabled_ci_builds')
            for build in disabled_ci_builds:
                print("\t\t %s: disabled" % (str(build)))

            print("\t Summary of Projects Status:")
            for build in qa_report_builds:
                qa_report_project = build.get('qa_report_project')
                if build.get('build_status') == "JOBSCOMPLETED":
                    print("\t\t %s %s, created at %s, %s ago, took %s" % (qa_report_project.get('full_name'),
                                                build.get('build_status'),
                                                build.get('created_at'),
                                                timesince(build.get('created_at')),
                                                build.get('duration')))
                else:
                    print("\t\t %s %s, created at %s, %s ago" % (qa_report_project.get('full_name'),
                                                build.get('build_status'),
                                                build.get('created_at'),
                                                timesince(build.get('created_at'))))

                numbers_of_result = build.get('numbers_of_result')
                str_numbers = "\t\t\t Summary: modules_total=%s, modules_done=%s, number_total=%s, number_failed=%s"
                print(str_numbers % (numbers_of_result.get('modules_total'),
                                        numbers_of_result.get('modules_done'),
                                        numbers_of_result.get('number_total'),
                                        numbers_of_result.get('number_failed')))
                str_numbers = "\t\t\t %s: modules_total=%s, modules_done=%s, number_total=%s, number_failed=%s"
                final_jobs = build.get('final_jobs')
                def get_job_name(item):
                    return item.get('name')
                sorted_jobs = sorted(final_jobs, key=get_job_name)

                for job in sorted_jobs:
                    job_name = job.get('name')
                    numbers_of_result = job.get('numbers')
                    if numbers_of_result is not None:
                        print(str_numbers % ("%s#%s %s" % (job_name, job.get('job_id'), job.get('job_status')),
                                            numbers_of_result.get('modules_total'),
                                            numbers_of_result.get('modules_done'),
                                            numbers_of_result.get('number_total'),
                                            numbers_of_result.get('number_failed')))

            print("\t Failures and Bugs:")

            project_platform_bugs = {} #cache bugs for the project and the platform
            for build in qa_report_builds:
                qa_report_project = build.get('qa_report_project')
                print("\t\t %s %s %s" % (qa_report_project.get('full_name'),
                                            build.get('build_status'),
                                            build.get('created_at')))

                self.get_bugs_and_failures_for_qabuild(build, cachepool=project_platform_bugs)

                classification = build.get('classification')
                bugs_reproduced = classification.get('bugs_reproduced')
                bugs_not_reproduced = classification.get('bugs_not_reproduced')
                new_failures = classification.get('new_failures')

                print("\t\t\t Bugs Reproduced: %s" % (len(bugs_reproduced)))
                for bug in bugs_reproduced:
                    print("\t\t\t\t %s %s %s" % (bug.id, bug.summary, bug.status))

                print("\t\t\t Bugs Not Reproduced: %s" % (len(bugs_not_reproduced)))
                for bug in bugs_not_reproduced:
                    print("\t\t\t\t %s %s %s" % (bug.id, bug.summary, bug.status))

                print("\t\t\t Failures Not Reported: %s" % (len(new_failures)))
                for failure in new_failures:
                    print("\t\t\t\t %s %s: %s" % (failure.get('module_name'), failure.get('test_name'), failure.get('message')))

        ircMsgList.append("KERNEL CHANGES STATUS REPORT FINISHED: %d in total" % num_kernelchanges)
        if len(ircMsgList) > 2:
            irc = IRC.getInstance()
            irc.sendAndQuit(msgStrOrAry=ircMsgList)
        else:
            # no completed kernel changes or no kernel changes in progress
            pass
