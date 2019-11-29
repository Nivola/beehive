# Changelog

## Version 1.6.0 (, 2019)

* Added ...
* Fixed ...
* Integrated ...
* Various bugfixes
    * changed method common.job.wait_for_job_complete. elapsed to set a job as stalled increased from 60s to 240s
    * correct bug in job_task. Celery worker does not release session if a task raise an Exception

## Version 1.5.0 (Sep 04, 2019)

* Added ...
    * added methods expunge, pre_expunge e post_expunge to ApiObject
    * added methods base_stmp2 and run2 in PaginatedQueryGenerator
    * added logger elk for api and task
    * added microsecond to event stored in mysql db
* Fixed ...
    * modify max query window for event to 2 hours
    * changed wait_for_job_complete. Timeout that identify a job as stalled is increased from 60s to 240s
* Integrated ...
    * added signature Celery that register task in redis when uuid is generated from the apply_async
    * added send of log item for the api class to elasticsearch if it is configured
* Various bugfixes

## Version 1.4.0 (May 24, 2019)

* Added ...
    * added field provider in the class classe common.model.authorization.User to indicate the autentication provider
    * added management of the field provider in the api of auth.user
* Fixed ...
    * revision of method user_request
    * modified query api of domains in query api of providers
    * modified configuration of the authentication provider ldap
    * update of the method get_entity signature: inserted params *args, **kvargs
    * Class GetAllTasksRequestSchema: corrected error in swagger validation, removed the parameter missing=None for 
      the field type
    * modified behaviour of the methid AbstractDbManager.add_perm_tag. Removed the rollback when permtag already exixsts
* Integrated ...
* Various bugfixes

## Version 1.3.0 (February 27, 2019)

* Added ...
    * added runner to realize concurrent test unit 
* Fixed ...
    * increased the size to 500 chars of the field desc in table event 
* Integrated ...
* Various bugfixes

## Version 1.2.0 (February 01, 2019)

* Added ...
    * **BeehiveApiClient** added method set_ssh_group_authorization
* Fixed ...
    * corrected bug in class PaginatedQueryGenerator that block change of group by filter
* Integrated ...
* Various bugfixes

## Version 1.1.0 (January 13, 2019)

* Added ...
    * added invoked job reference in caller task
* Fixed ...
    * trace: changed event trace. It was printed the name of the traced method
    * event: revision of the list query. It is too slow. Query was limited to one day.
    * auth: revision of the method that control user has a specific role
* Integrated ...
* Various bugfixes

## Version 1.0.0 (July 31, 2018)

First production preview release.

## Version 0.1.0 (April 18, 2016)

First private preview release.