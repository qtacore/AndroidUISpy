# -*- coding: UTF-8 -*-
#
# Tencent is pleased to support the open source community by making QTA available.
# Copyright (C) 2016THL A29 Limited, a Tencent company. All rights reserved.
# Licensed under the BSD 3-Clause License (the "License"); you may not use this 
# file except in compliance with the License. You may obtain a copy of the License at
# 
# https://opensource.org/licenses/BSD-3-Clause
# 
# Unless required by applicable law or agreed to in writing, software distributed 
# under the License is distributed on an "AS IS" basis, WITHOUT WARRANTIES OR CONDITIONS
# OF ANY KIND, either express or implied. See the License for the specific language
# governing permissions and limitations under the License.
#

'''Activity管理
'''

import re
from manager import BaseManager

class TaskStack(object):
    '''任务栈
    '''
    def __init__(self, _id):
        self._id = _id
        self._tasks = []
    
    def __str__(self):
        result = 'TaskStack #%d\n' % self._id
        for task in self._tasks:
            result += '%s\n' % task
        return result
    
    @property
    def task_list(self):
        return self._tasks
    
    def add_task(self, task):
        self._tasks.append(task)
        
class Task(object):
    '''任务
    '''
    def __init__(self, _id):
        self._id = _id
        self._task_record = None
        self._activities = [] 
    
    def __str__(self):
        result = '<Task at 0x%X Record=%s>\n' % (id(self), self._task_record)
        for activity in self._activities:
            result += '%s\n' % activity
        return result
    
    @property
    def task_record(self):
        return self._task_record
    
    @task_record.setter
    def task_record(self, record):
        self._task_record = record
    
    @property
    def activity_list(self):
        return self._activities
    
    def add_activity(self, activity):
        '''
        '''
        self._activities.append(activity)
        
class TaskRecord(object):
    '''
    '''
    def __init__(self, hashcode, task_id, package_name):
        self._hashcode = hashcode
        self._task_id = task_id
        self._package_name = package_name
    
    def __str__(self):
        return '<TaskRecord at 0x%X hashcode=0x%s id=%d package_name=%s>' % (id(self), self._hashcode, self._task_id, self._package_name)
    
class Activity(object):
    '''
    '''
    def __init__(self, _id, activity_record):
        self._id = _id
        self._activity_record = activity_record
        self._attrs = {}
    
    @property
    def name(self):
        '''Activity名称
        '''
        activity = self._attrs.get('realActivity', 'None')
        if '/' in activity:
            pkg, activity = activity.split('/')
            if activity[0] == '.':
                activity = pkg + activity
        return activity
    
    @property
    def package_name(self):
        '''所在包名
        '''
        return self._attrs['packageName']
    
    @property
    def process_name(self):
        '''所在进程名
        '''
        return self._attrs['processName']
    
    def __setitem__(self, key, val):
        self._attrs[key] = val
        
    def __str__(self):
        result = '<Activity at 0x%X id=%d activity_record=%s ' % (id(self), self._id, self._activity_record)
        for attr in self._attrs:
            result += '%s=%s ' % (attr, self._attrs[attr])
        result += '>'
        return result
    
class ActivityRecord(object):
    '''Activity记录
    '''  
    def __init__(self, hashcode, task_id, activity):
        self._hashcode = hashcode
        self._task_id = task_id
        self._activity = activity
        
    
class ActivityManager(BaseManager):
    '''Activity管理
    '''
    
    def __init__(self, device):
        self._device = device
        self._activities_data = None
    
    def update(self):
        '''
        '''
        self._activities_data = None
        
    def get_activity_list(self):
        if not self._activities_data:
            self._activities_data = self._get_activities_data()
        result = []
        for stack in self._activities_data:
            for task in stack.task_list:
                for activity in task.activity_list:
                    result.append(activity)
        return result
    
    def _get_activities_data(self):
        '''获取并解析activity数据
        '''
        result = self._device.adb.run_shell_cmd('dumpsys activity activities')
        result = result.replace('\r', '')
        # print result
        p1 = re.compile(r'^  Stack #(\d+).*:.*$')
        p2 = re.compile(r'^    Task id #(\d+)$')
        p3 = re.compile(r'^\s+\* TaskRecord\{(\w{6,8}) #(\d+)(.+)}$')
        p4 = re.compile(r'^\s+\* Hist #(\d+): ActivityRecord{(\w{5,8})(.+)}$')
        stack = None
        task = None
        hist = None
        stacks = []

        for line in result.split('\n')[1:]:
            if not line: 
                task = None
                continue
            # print repr(line)
            if 'mLastPausedActivity:' in line:
                stack = None
                continue
            if stack == None:
                if line == '  Main stack:':
                    stack = TaskStack(0)
                    stacks.append(stack)
                    task = Task(0)
                    stack.add_task(task)
                else:
                    ret = p1.match(line)
                    if ret: 
                        stack_id = int(ret.group(1)) if not isinstance(ret, bool) else 0
                        stack = TaskStack(stack_id)
                        stacks.append(stack)
            elif task == None:
                ret = p2.match(line)
                if ret:
                    task = Task(int(ret.group(1)))
                    stack.add_task(task)
            elif task.task_record == None:
                ret = p3.match(line)
                if ret:
                    package_name = ''
                    items = ret.group(3).strip().split(' ')
                    for item in items:
                        if not '=' in item: continue
                        key, val = item.split('=')
                        if key == 'A':
                            package_name = val
                            break
                    task_record = TaskRecord(ret.group(1), int(ret.group(2)), package_name)
                    task.task_record = task_record
            elif hist == None:
                ret = p4.match(line)
                if ret:
                    activity = ''
                    task_id = 0
                    items = ret.group(3).strip().split(' ')
                    for item in items:
                        if '/' in item:
                            activity = item
                        elif item[0] == 't':
                            task_id = int(item[1:])
                    activity_record = ActivityRecord(ret.group(2), task_id, activity)
                    hist = Activity(int(ret.group(1)), activity_record)
                    task.add_activity(hist)
            elif line.startswith('    '):
                items = line.split(' ')
                for item in items:
                    if not '=' in item: continue
                    pos = item.find('=')
                    key = item[:pos]
                    val = item[pos + 1:]
                    if key in ['processName', 'packageName', 'realActivity', 'state']:
                        hist[key] = val
                if 'waitingVisible' in line:
                    hist = None
        return stacks
     
if __name__ == '__main__':
    pass
