## https://docs.djangoproject.com/en/1.11/topics/db/managers/
## https://docs.djangoproject.com/en/dev/howto/custom-management-commands/#howto-custom-management-commands
## https://medium.com/@bencleary/django-scheduled-tasks-queues-part-1-62d6b6dc24f8
## https://medium.com/@bencleary/django-scheduled-tasks-queues-part-2-fc1fb810b81d
## https://medium.com/@kevin.michael.horan/scheduling-tasks-in-django-with-the-advanced-python-scheduler-663f17e868e6
## https://django-background-tasks.readthedocs.io/en/latest/
# VtsKernelLinuxKselftest#timers_set-timer-lat_32bit
import pdb
import datetime
import json
import logging
import os
import re
import yaml
from dateutil import parser
import datetime

from django.core.management.base import BaseCommand, CommandError

from django.utils.timesince import timesince

from lkft.models import KernelChange, CiBuild, ReportBuild

from lcr import qa_report

from lcr.settings import QA_REPORT, QA_REPORT_DEFAULT, BUILD_WITH_JOBS_NUMBER

from lkft.views import get_test_result_number_for_build, get_lkft_build_status
from lkft.views import extract
from lkft.views import get_result_file_path
from lkft.views import download_attachments_save_result, get_classified_jobs
from lkft.lkft_config import get_version_from_pname, get_kver_with_pname_env

logger = logging.getLogger(__name__)

qa_report_def = QA_REPORT[QA_REPORT_DEFAULT]
qa_report_api = qa_report.QAReportApi(qa_report_def.get('domain'), qa_report_def.get('token'))
jenkins_api = qa_report.JenkinsApi('ci.linaro.org', None)

rawkernels = {
   '4.4':[
            '4.4p-10.0-gsi-hikey',
            '4.4p-9.0-hikey',
            '4.4o-10.0-gsi-hikey',
            '4.4o-9.0-lcr-hikey',
            '4.4o-8.1-hikey',
            ],
   '4.9':[ 
            '4.9q-10.0-gsi-hikey960',
            '4.9q-10.0-gsi-hikey',
            '4.9p-10.0-gsi-hikey960',
            '4.9p-10.0-gsi-hikey',
            '4.9o-10.0-gsi-hikey960',
            '4.9p-9.0-hikey960',
            '4.9p-9.0-hikey',
            '4.9o-10.0-gsi-hikey',
            '4.9o-9.0-lcr-hikey',
            '4.9o-8.1-hikey', 
            ],
   '4.14':[ 
            '4.14-stable-master-hikey960-lkft',
            '4.14-stable-master-hikey-lkft',
            '4.14-stable-aosp-x15',
            '4.14q-10.0-gsi-hikey960',
            '4.14q-10.0-gsi-hikey',
            '4.14p-10.0-gsi-hikey960',
            '4.14p-10.0-gsi-hikey',
            '4.14p-9.0-hikey960',
            '4.14p-9.0-hikey',
            ],
   '4.19':[ 
            '4.19q-10.0-gsi-hikey960',
            '4.19q-10.0-gsi-hikey',
            '4.19-stable-aosp-x15',
            '4.19-stable-master-hikey-lkft',
            '4.19-stable-master-hikey960-lkft',
            ],
   '5.4':[ 
            '5.4-gki-aosp-master-db845c',
            '5.4-gki-aosp-master-hikey960',
            '5.4-aosp-master-x15',
            '5.4-gki-android11-android11-hikey960',
            '5.4-gki-android11-android11-db845c',
            '5.4-lts-gki-android11-android11-hikey960',
            '5.4-lts-gki-android11-android11-db845c',
            ],
}

projectids = {
   '4.4o-8.1-hikey': 
                    {'project_id': 86, 
                     'hardware': 'HiKey',
                     'OS' : 'LCR-Android8',
                     'baseOS' : 'Android8',
                     'kern' : '4.4',
                     'branch' : 'Android-4.4-o',}, 
   '4.4o-9.0-lcr-hikey':
                    {'project_id': 253, 
                     'hardware': 'HiKey',
                     'OS' : 'LCR-Android9',
                     'baseOS' : 'Android9',
                     'kern' : '4.4',
                     'branch' : 'Android-4.4-o',},
   '4.4o-10.0-gsi-hikey':
                    {'project_id': 254, 
                     'hardware': 'HiKey',
                     'OS' : 'Android10',
                     'kern' : '4.4',
                     'branch' : 'Android-4.4-o',},
   '4.4p-9.0-hikey':
                    {'project_id': 123, 
                     'hardware': 'HiKey',
                     'OS' : 'LCR-Android9',
                     'baseOS' : 'Android9',
                     'kern' : '4.4',
                     'branch' : 'Android-4.4-p',},
   '4.4p-10.0-gsi-hikey':
                    {'project_id': 225, 
                     'hardware': 'HiKey',
                     'OS' : 'Android10',
                     'kern' : '4.4',
                     'branch' : 'Android-4.4-p',},
   '4.9o-8.1-hikey':
                    {'project_id': 87, 
                     'hardware': 'HiKey',
                     'OS' : 'LCR-Android8',
                     'baseOS' : 'Android8',
                     'kern' : '4.9',
                     'branch' : 'Android-4.9-o',},
   '4.9o-9.0-lcr-hikey':
                    {'project_id': 250, 
                     'hardware': 'HiKey',
                     'OS' : 'LCR-Android9',
                     'baseOS' : 'Android9',
                     'kern' : '4.9',
                     'branch' : 'Android-4.9-o',},
   '4.9o-10.0-gsi-hikey':
                    {'project_id': 251, 
                     'hardware': 'HiKey',
                     'OS' : 'Android10',
                     'kern' : '4.9',
                     'branch' : 'Android-4.9-o',},
   '4.9o-10.0-gsi-hikey960':
                    {'project_id': 255, 
                     'hardware': 'HiKey960',
                     'OS' : 'Android10',
                     'kern' : '4.9',
                     'branch' : 'Android-4.9-o',},
   '4.9p-9.0-hikey':
                    {'project_id': 122, 
                     'hardware': 'HiKey',
                     'OS' : 'LCR-Android9',
                     'baseOS' : 'Android9',
                     'kern' : '4.9',
                     'branch' : 'Android-4.9-p',},
   '4.9p-9.0-hikey960':
                    {'project_id': 179,
                     'hardware': 'HiKey960',
                     'OS' : 'LCR-Android9',
                     'baseOS' : 'Android9',
                     'kern' : '4.9',
                     'branch' : 'Android-4.9-p',},
   '4.9p-10.0-gsi-hikey':
                    {'project_id': 223,
                     'hardware': 'HiKey',
                     'OS' : 'Android10',
                     'kern' : '4.9',
                     'branch' : 'Android-4.9-p',},
   '4.9p-10.0-gsi-hikey960':
                    {'project_id': 222, 
                     'hardware': 'HiKey960',
                     'OS' : 'Android10',
                     'kern' : '4.9',
                     'branch' : 'Android-4.9-p',},
   '4.9q-10.0-gsi-hikey':
                    {'project_id': 212, 
                     'hardware': 'HiKey',
                     'OS' : 'Android10',
                     'kern' : '4.9',
                     'branch' : 'Android-4.9-q',},
   '4.9q-10.0-gsi-hikey960':
                    {'project_id': 213, 
                     'hardware': 'HiKey960',
                     'OS' : 'Android10',
                     'kern' : '4.9',
                     'branch' : 'Android-4.9-q',},
   '4.14p-9.0-hikey':
                    {'project_id': 121, 
                     'hardware': 'HiKey',
                     'OS' : 'LCR-Android9',
                     'baseOS' : 'Android9',
                     'kern' : '4.14',
                     'branch' : 'Android-4.14-p',},
   '4.14p-9.0-hikey960':
                    {'project_id': 177, 
                     'hardware': 'HiKey960',
                     'OS' : 'LCR-Android9',
                     'baseOS' : 'Android9',
                     'kern' : '4.14',
                     'branch' : 'Android-4.14-p',},
   '4.14p-10.0-gsi-hikey':
                    {'project_id': 220, 
                     'hardware': 'HiKey',
                     'OS' : 'Android10',
                     'kern' : '4.14',
                     'branch' : 'Android-4.14-p',},
   '4.14p-10.0-gsi-hikey960':
                    {'project_id': 221, 
                     'hardware': 'HiKey960',
                     'OS' : 'Android10',
                     'kern' : '4.14',
                     'branch' : 'Android-4.14-p',},
   '4.14q-10.0-gsi-hikey':
                    {'project_id': 211, 
                     'hardware': 'HiKey',
                     'OS' : 'Android10',
                     'kern' : '4.14',
                     'branch': 'Android-4.14-q',},
   '4.14q-10.0-gsi-hikey960':
                    {'project_id': 214,
                     'hardware': 'HiKey960',
                     'OS' : 'Android10',
                     'kern' : '4.14',
                     'branch' : 'Android-4.14-q',},
   '4.14-stable-aosp-x15':
                    {'project_id': 320,
                     'hardware': 'X15',
                     'OS' : 'AOSP',
                     'kern' : '4.14',
                     'branch' : 'Android-4.14-stable',},
   '4.14-stable-master-hikey-lkft':
                    {'project_id': 297, 
                     'hardware': 'HiKey',
                     'OS' : 'AOSP',
                     'kern' : '4.14',
                     'branch': 'Android-4.14-stable',},
   '4.14-stable-master-hikey960-lkft':
                    {'project_id': 298, 
                     'hardware': 'HiKey960',
                     'OS' : 'AOSP',
                     'kern' : '4.14',
                     'branch': 'Android-4.14-stable',},
   '4.19q-10.0-gsi-hikey':
                    {'project_id': 210, 
                     'hardware': 'HiKey',
                     'OS' : 'Android10',
                     'kern' : '4.19',
                     'branch' : 'Android-4.19-q',},
   '4.19q-10.0-gsi-hikey960':
                    {'project_id': 215, 
                     'hardware': 'HiKey960',
                     'OS' : 'Android10',
                     'kern' : '4.19',
                     'branch' : 'Android-4.19-q',},
   '4.19-stable-aosp-x15':
                    {'project_id': 335,
                     'hardware': 'x15',
                     'OS' : 'AOSP',
                     'kern' : '4.19',
                     'branch' : 'Android-4.19-stable',},
    '4.19-stable-master-hikey-lkft':
                    {'project_id': 299,
                     'hardware': 'hikey',
                     'OS' : 'AOSP',
                     'kern' : '4.19',
                     'branch' : 'Android-4.19-stable',},
    '4.19-stable-master-hikey960-lkft':
                    {'project_id': 300,
                     'hardware': 'hikey960',
                     'OS' : 'AOSP',
                     'kern' : '4.19',
                     'branch' : 'Android-4.19-stable',},
   '5.4-gki-aosp-master-hikey960':
                    {'project_id': 257, 
                     'hardware': 'HiKey960',
                     'OS' : 'AOSP',
                     'kern' : '5.4',
                     'branch' : 'Android-5.4',},
   '5.4-gki-aosp-master-db845c':
                    {'project_id': 261,
                     'hardware': 'db845',
                     'OS' : 'AOSP',
                     'kern' : '5.4',
                     'branch' : 'Android-5.4',},
   '5.4-stable-gki-aosp-master-hikey960':
                    {'project_id': 296, 
                     'hardware': 'HiKey960',
                     'kern' : '5.4',
                     'OS' : 'AOSP',
                     'branch' : 'Android-5.4-stable',},
   '5.4-stable-gki-aosp-master-db845c':
                    {'project_id': 295,
                     'hardware': 'db845',
                     'OS' : 'AOSP',
                     'kern' : '5.4',
                     'branch' : 'Android-5.4-stable',},
   '5.4-aosp-master-x15':
                    {'project_id': 339,
                     'hardware': 'x15',
                     'OS' : 'AOSP',
                     'kern' : '5.4',
                     'branch' : 'Android-5.4',},
   '5.4-gki-android11-android11-db845c':
                    {'project_id': 414,
                     'hardware': 'db845',
                     'OS' : 'Android11',
                     'kern' : '5.4',
                     'branch' : 'Android-5.4',},
   '5.4-gki-android11-android11-hikey960':
                    {'project_id': 409,
                     'hardware': 'hikey960',
                     'OS' : 'Android11',
                     'kern' : '5.4',
                     'branch' : 'Android-5.4',},
   '5.4-lts-gki-android11-android11-db845c':
                    {'project_id': 524,
                     'hardware': 'db845',
                     'OS' : 'Android11',
                     'kern' : '5.4',
                     'branch' : 'Android-5.4-lts',},
   '5.4-lts-gki-android11-android11-hikey960':
                    {'project_id': 519,
                     'hardware': 'hikey960',
                     'OS' : 'Android11',
                     'kern' : '5.4',
                     'branch' : 'Android-5.4-lts',},
}

def do_boilerplate(output):
    output.write("Failure Key:\n")
    output.write("--------------------\n")
    output.write("I == Investigation\nB == Bug#, link to bugzilla\nF == Flakey\nU == Unexpected Pass\n\n")

# a flake entry
# name, state, bugzilla
def process_flakey_file(flakefile):
    Dict44 = {'version' : 4.4 , 'flakelist' : [] }
    Dict49 = {'version' : 4.9 , 'flakelist' : [] }
    Dict414 = {'version' : 4.14, 'flakelist' : [] }
    Dict419 = {'version' : 4.19, 'flakelist' : [] }
    Dict54 = {'version' : 5.4, 'flakelist' : [] }
    flakeDicts = [Dict44, Dict49, Dict414, Dict419, Dict54]

    kernelsmatch = re.compile('[0-9]+.[0-9]+')
    androidmatch = re.compile('ANDROID[0-9]+|AOSP')
    hardwarematch = re.compile('HiKey|db845|HiKey960')
    allmatch = re.compile('ALL')
    #pdb.set_trace()
    Lines = flakefile.readlines()
    for Line in Lines:
        newstate = ' '
        if Line[0] == '#':
            continue
        if Line[0] == 'I' or Line[0] == 'F' or Line[0] == 'B' or Line[0] == 'E':
            newstate = Line[0]
            Line = Line[2:]
        m = Line.find(' ')
        if m:
            testname = Line[0:m]
            Line = Line[m:]
            testentry = {'name' : testname, 'state': newstate, 'board': [], 'androidrel':[] }
            if Line[0:4] == ' ALL':
               Line = Line[5:]
               Dict44['flakelist'].append(testentry)
               Dict49['flakelist'].append(testentry)
               Dict414['flakelist'].append(testentry)
               Dict419['flakelist'].append(testentry)
               Dict54['flakelist'].append(testentry)
            else:
               n = kernelsmatch.match(Line)
               if n:
                  Line = Line[n.end():]
                  for kernel in n:
                      for Dict in flakeDicts:
                          if kernel == Dict['version']:
                              Dict['flakelist'].append(testentry)
               else:
                   continue 
            if Line[0:3] == 'ALL':
               Line = Line[4:]
               testentry['board'].append("HiKey")
               testentry['board'].append("HiKey960")
               testentry['board'].append("db845")
            else:
               h = hardwarematch.findall(Line)
               if h:
                  for board in h:
                      testentry['board'].append(board)
               else:
                   continue
            a = allmatch.search(Line)
            if a:
               testentry['androidrel'].append('Android8')
               testentry['androidrel'].append('Android9')
               testentry['androidrel'].append('Android10')
               testentry['androidrel'].append('Android11')
               testentry['androidrel'].append('AOSP')
            else:
               a = androidmatch.findall(Line)
               if a:
                  for android in a:
                      testentry['androidrel'].append(android)
               else:
                   continue
        else:
            continue 
       
    return flakeDicts

# take the data dictionaries, the testcase name and ideally the list of failures
# and determine how to classify a test case. This might be a little slow espeically
# once linked into bugzilla
def classifyTest(flakeDicts, testcasename, hardware, kernel, android):
    for dict in flakeDicts:
        if dict['version'] == kernel:
            break
    #pdb.set_trace()
    foundboard = 0
    foundandroid = 0
    #if testcasename == 'VtsKernelLinuxKselftest.timers_set-timer-lat_64bit':
    #    pdb.set_trace()
    #if testcasename == 'android.webkit.cts.WebChromeClientTest#testOnJsBeforeUnloadIsCalled#arm64-v8a':
    #    pdb.set_trace()
    for flake in dict['flakelist']:
        if flake['name'] == testcasename:
            for board in flake['board'] :
                if board == hardware:
                    foundboard = 1
                    break
            for rel in flake['androidrel']:
                if rel == android:
                    foundandroid = 1
                    break
            if foundboard == 1 and foundandroid == 1:
                return flake['state']
            else:
                return 'I'
    return 'I'


def versiontoMME(versionString):
    versionDict = { 'Major':0,
                    'Minor':0,
                    'Extra':0, }

    if versionString.startswith('v'):
        versionString = versionString[1:]
    # print versionString
    tokens = re.split( r'[.-]', versionString)
    # print tokens
    if tokens[0].isnumeric() and tokens[1].isnumeric() and tokens[2].isnumeric():
        versionDict['Major'] = tokens[0]
        versionDict['Minor'] = tokens[1]
        versionDict['Extra'] = tokens[2]

    return versionDict


# set the last finished job for boot/cts/vts types
def markjob(job, jobTransactionStatus):
    vtsSymbol = re.compile('-vts-')
    bootSymbol = re.compile('boot')
    ctsSymbol = re.compile('-cts')

    vtsresult = vtsSymbol.search(job['name'])
    bootresult = bootSymbol.search(job['name'])
    ctsresult = ctsSymbol.search(job['name'])

    newjobTime = parser.parse(job['created_at'])
    if vtsresult is not None:
       jobTransactionStatus['vts'] = 'true'
       # take the later of the two results
       if jobTransactionStatus['vts-job'] is None:
           jobTransactionStatus['vts-job'] = job
       else:
           origjobTime = parser.parse(jobTransactionStatus['vts-job']['created_at'])
           if newjobTime > origjobTime :
               jobTransactionStatus['vts-job'] = job
    if ctsresult is not None :
       jobTransactionStatus['cts'] = 'true'
       # take the later of the two results
       if jobTransactionStatus['cts-job'] is None:
           jobTransactionStatus['cts-job'] = job
       else:
           origjobTime = parser.parse(jobTransactionStatus['cts-job']['created_at'])
           if newjobTime > origjobTime :
               jobTransactionStatus['cts-job'] = job
    if bootresult is not None :
       jobTransactionStatus['boot'] = 'true'
       # take the later of the two results
       if jobTransactionStatus['boot-job'] is None:
           jobTransactionStatus['boot-job'] = job
       else:
           origjobTime = parser.parse(jobTransactionStatus['boot-job']['created_at'])
           if newjobTime > origjobTime :
               jobTransactionStatus['boot-job'] = job

    

def find_best_two_runs(builds, project_name, project):
    goodruns = []
    bailaftertwo = 0
    number_of_build_with_jobs = 0
    baseVersionDict = None
    nextVersionDict = None

    for build in builds:
        if bailaftertwo == 2:
            break
        build['created_at'] = qa_report_api.get_aware_datetime_from_str(build.get('created_at'))
        jobs = qa_report_api.get_jobs_for_build(build.get("id"))
        jobs_to_be_checked = get_classified_jobs(jobs=jobs).get('final_jobs')
        build_status = get_lkft_build_status(build, jobs_to_be_checked)
        if build_status['has_unsubmitted']:
            #print "has unsubmitted"
            continue
        elif build_status['is_inprogress']:
            #print "in progress"
            continue

        build['numbers'] = qa_report.TestNumbers()
        build['jobs'] = jobs
        #if build_number_passed == 0:
        #    continue

        download_attachments_save_result(jobs=jobs_to_be_checked)

        temp_build_numbers = get_test_result_number_for_build(build, jobs_to_be_checked)
        jobs_finished = temp_build_numbers.get('jobs_finished')
        jobs_total = temp_build_numbers.get('jobs_total')
        if jobs_finished != jobs_total:
          # not all jobs finished successfully, this build will be ignored
          print("build ignored as not all jobs finished successfully: project_name=%s, build['version']=%s, jobs_finished=%d, jobs_total=%d" % (project_name, build['version'], jobs_finished, jobs_total))
          continue

        build['numbers'].addWithHash(temp_build_numbers)

        failures = {}
        # pdb.set_trace()
        for job in jobs_to_be_checked:
           result_file_path = get_result_file_path(job=job)
           if not result_file_path or not os.path.exists(result_file_path):
              continue
           # now tally then move onto the next job
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

        if bailaftertwo == 0 :
          baseVersionDict = versiontoMME(build['version'])
          # print "baseset"
        elif bailaftertwo == 1 :
          nextVersionDict = versiontoMME(build['version'])
          if nextVersionDict['Extra'] == baseVersionDict['Extra'] :
            continue

        goodruns.append(build)
        bailaftertwo += 1

        failures_list = []
        for module_name in sorted(failures.keys()):
            failures_in_module = failures.get(module_name)
            for test_name in sorted(failures_in_module.keys()):
                failure = failures_in_module.get(test_name)
                abi_stacktrace = failure.get('abi_stacktrace')
                abis = sorted(abi_stacktrace.keys())

                stacktrace_msg = ''
                if (len(abis) == 2) and (abi_stacktrace.get(abis[0]) != abi_stacktrace.get(abis[1])):
                    for abi in abis:
                        stacktrace_msg = '%s\n\n%s:\n%s' % (stacktrace_msg, abi, abi_stacktrace.get(abi))
                else:
                    stacktrace_msg = abi_stacktrace.get(abis[0])

                failure['abis'] = abis
                failure['stacktrace'] = stacktrace_msg.strip()

                failures_list.append(failure)

        android_version = get_version_from_pname(pname=project.get('name'))
        build['failures_list'] = failures_list

    return goodruns

# found the failures that in goodruns[0], but not in goodruns[1]
# return goodruns[0]-goodruns[1]
def find_regressions(goodruns):
    runA = goodruns[0]
    failuresA = runA['failures_list']
    runB = goodruns[1]
    failuresB = runB['failures_list']
    regressions = []
    for failureA in failuresA:
        match = 0
        testAname = failureA['test_name']
        for failureB in failuresB:
            testBname = failureB['test_name']
            if testAname == testBname:
                match = 1
                break
        if match != 1 :
            regressions.append(failureA)
    return regressions

# found the failures that in goodruns[1], but not in goodruns[0]
# return goodruns[1] - goodruns[0]
def find_antiregressions(goodruns):
    runA = goodruns[0]
    failuresA = runA['failures_list']
    runB = goodruns[1]
    failuresB = runB['failures_list']
    antiregressions = []
    for failureB in failuresB:
        match = 0
        for failureA in failuresA:
            testAname = failureA['test_name']
            testBname = failureB['test_name']
            if testAname == testBname:
                match = 1
                break
        if match != 1 :
            antiregressions.append(failureB)
    return antiregressions


"""  Example project_info dict
                    {'project_id': 210, 
                     'hardware': 'hikey',
                     'OS' : 'Android10',
                     'branch' : 'Android-4.19-q',},
"""

def print_androidresultheader(output, project_info, run, priorrun ):
        output.write("    " + project_info['OS'] + "/" + project_info['hardware'] + " - " )
        output.write("Current:" + run['version'] + "  Prior:" + priorrun['version']+"\n")

def add_unique_kernel(unique_kernels, kernel_version):
    if kernel_version not in unique_kernels:
        unique_kernels.append(kernel_version)


def report_results(output, run, regressions, combo, priorrun, flakes, antiregressions):
    jobs = run['jobs']
    job = jobs[0]
    #pdb.set_trace()
    numbers = run['numbers']
    project_info = projectids[combo]
    output.write(project_info['branch'] + "\n")
    print_androidresultheader(output, project_info, run, priorrun)
    #pdb.set_trace()
    output.write("    " + str(len(regressions)) + " Regressions ")
    output.write(str(numbers.number_failed) + " Failures ")
    output.write(str(numbers.number_passed) + " Passed ")
    output.write( str(numbers.number_total) + " Total - " )
    output.write("Modules Run: " + str(numbers.modules_done) + " Module Total: "+str(numbers.modules_total)+"\n")
    output.write("    "+str(len(antiregressions)) + " Prior Failures now pass\n")
    for regression in regressions:
        # pdb.set_trace()
        if 'baseOS' in project_info: 
            OS = project_info['baseOS']
        else:
            OS = project_info['OS']
        testtype=classifyTest(flakes, regression['test_name'], project_info['hardware'], project_info['kern'], OS)
        # def classifyTest(flakeDicts, testcasename, hardware, kernel, android):
        output.write("        " + testtype + " " + regression['test_name'] + "\n")


def report_kernels_in_report(output, unique_kernels): 
    output.write("\n")
    output.write("\n")
    output.write("Kernels in this report:\n")
    for kernel in unique_kernels:
        output.write("    " + kernel+"\n")


class Command(BaseCommand):
    help = 'returns Android Common Kernel Regression Report for specific kernels'

    def add_arguments(self, parser):
        parser.add_argument('kernel', type=str, help='Kernel version')
        parser.add_argument('outputfile', type=str, help='Output File')
        parser.add_argument('flake', type=str, help='flakey file')

    def handle(self, *args, **options):
        kernel = options['kernel']
        output = open(options['outputfile'], "w")
        flakefile = open(options['flake'], "r")

        # map kernel to all available kernel, board, OS combos that match
        work = []
        unique_kernels=[]

        work = rawkernels[kernel]
        flakes = process_flakey_file(flakefile)

        do_boilerplate(output)

        for combo in work:
            project_info = projectids[combo]
            project_id = project_info['project_id']
            project =  qa_report_api.get_project(project_id)
            builds = qa_report_api.get_all_builds(project_id)
            project_name = project.get('name')
            goodruns = find_best_two_runs(builds, project_name, project)
            if len(goodruns) < 2 :
                print("\nERROR project " + project_name+ " did not have 2 good runs\n")
                output.write("\nERROR project " + project_name+ " did not have 2 good runs\n\n")
            else:
                add_unique_kernel(unique_kernels, goodruns[0]['version'])
                regressions = find_regressions(goodruns)
                antiregressions = find_antiregressions(goodruns)
                report_results(output, goodruns[0], regressions, combo, goodruns[1], flakes, antiregressions)
        report_kernels_in_report(output, unique_kernels)
        output.close()
        
"""
        except:
            raise CommandError('Kernel "%s" does not exist' % kernel)
"""
