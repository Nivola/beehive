# Changelog

## Version 1.16.0 (2024-03-26)

Rilascio nuove funzionalità
* Added
  - maintenance mode check user is SuperAdmin
  - api_timeout_max, custom header CSI-Nvl-Timeout, and formatting changes
  - user taxcode, ldap (insert, update, list)
  - Add commented lines to profile
* Fixed
  - map[test:failfast to break tests in case of error]
  - map[fix get_ssh_user:check len list users]
  - task log debug
  - map[auth:fix list size, type hint]
  - map[test:Call api elapsed]
  - script sql add table users taxcode, ldap
  - fix method patch in ApiView. check_permission
  - fix user update email
  - Fix worngly used time
  - Use ujson
  - Try to rearrange imports in rando order

## Version 1.15.3 (2024-03-11)

Rilascio nuove funzionalità
* Added
  - Aggiunta modo maintenance mode
  - map[maintenance:change response http code 503 when in maintenance]
  - map[maintenance:API check]
* Fixed
  - fix test_run_test_task1
  - fix swagger StatusAPI
  - set version v1.15.3
  - redis_manager instance of RedisManager (redis.StrictRedis old)
  - fix method patch in ApiView. check_permission

## Version 1.15.0 (2025-10-12)

Rilascio nuove funzionalità
* Added
  - http request/response auditing
  - task auditing
* Fixed
  - timeout
  - check permission
  - audit log fields

## Version 1.14.0 (2023-06-22)

Rilascio nuove funzionalità
* Added
  - check permissions for api method executions
* Fixed
  - identity crud refactored
  - refactoring controller
  - minor fixes

## Version 1.13.0 (2023-02-24)

Rilascio nuove funzionalità
* Fixed
  - minor fixes

## Version 1.12.0 (2023-01-27)

Rilascio nuove funzionalità
* Added
  - version 8 elastisearch
* Fixed
  - minor fixes

## Version 1.11.0 (2022-02-11)

Rilascio nuove funzionalità
* Added
  - add decorator and methods to declare ApiObject method as async. Method is executed as Celery task
  - add system to remove user tokens when permissions change
  - add redis ping in base api
  - add step name in event trace api
  - removed field expiry_date from authorization Role
  - add print of pod name in event destination
  - add user role creation for admin user in auth manager add_user. Add role user for admin@local in auth user table
* Fixed
  - sql join in get_paginated_entities using run2 method
  - correct aut object type and object action open api definition
  - add clean_cache in ApiObject update, delete, expunge method
  - correct incompatibility with last version of sql alchemy and Flask
  - correct bug in redis identity connection
  - correct bug in use of redis as session interface

## Version 1.10.0 (2021-06-11)

Rilascio nuove funzionalità
* Added
  - add method ApiObject.cache_data to cache data from a function
  - add beehive_service_netaas logger
  - removed logging handler to elastic
  - integrated event saving in elastic using logstash
  - correct logging format to enable best management with filebeat and logstash
  - integrated usage of different redis for identity and cache management

## Version 1.9.0 (2021-02-05)

Rilascio nuove funzionalità
* Added
  - add new api ping (with sql check), capabilities and version to /v1.0/nas, /v1.0/nes, /v1.0/nws, /v1.0/nrs, /v1.0/gas
  - add ApiObject pre_clone and post_clone method
  - add method set_ssh_key_authorization to ApiClient

## Version 1.8.0 (2020-12-31)

Rilascio nuove funzionalità
* Added
  - update version setup
* Fixed
  - add BeehiveApiClient method set_endpoints to set endpoints manually
* Changed
  - update copyright
* Removed
  - removed old python 2 start script from server package

## Version 1.7.2 (2020-09-10)

Rilascio nuove funzionalità
* Fixed
  - removed unused startup configuration
  - now configuration can be passed using only the uwsgi config file
  - replaced redis queue with rabbitmq queue in catalog consumer and producer
  - added ApiClient method get_ssh_user
  - add ApiObject method get_cache
  - correct some configuration issue
  - correct bug in get_permissions_groups, get_permissions_users and get_permissions_roles. Int perm id can nat get correctly
  - correct bug in method ApiObject set_cache
  - correct bug in get_entity. Entity None was not intercepted

## Version 1.7.1 (2020-06-17)

Rilascio nuove funzionalità
* Added
  - added task manager batch to run task using scheduled k8s pod
  - added batch server to run task manager using scheduled k8s pod
* Fixed
  - add print of security log from event to rsyslog
  - correct bug in base model update_entity. Added synchronize_session=False to resolve a problem in update
  - correct bugs in ApiClient
  - correct bug un PaginatedQueryGenerator that return wrong number of records. Added param group_by to set as True when call run with with_permtag=False

## Version 1.7.0 (2020-06-21)

Rilascio nuove funzionalità
* Added
  - api_client create_token can use also client authentication. Use this one for cmp instances communication
  - new task engine implementation based on single celery task and step function (common.task_v2, module.scheduler_v2)
  - wait_task and admin_wait_task method in ApiClient
  - replaced EventProducerRedis with EventProducerKombu configured to use rabbitmq
  - EventConsumerRedis changed in EventConsumer and configured to use rabbitmq
* Fixed
  - fixed a misbehavior of add_perm_tag method used with ssh module (group, node, user and key are permtag are not created). Added session.commit() before second transaction block
  - improve performance of methods append_permisssions, remove_permisssions, get_permisssions

## Version 1.6.0 (2019-12-23)

Rilascio nuove funzionalità
* Fixed
  - changed method common.job.wait_for_job_complete. elapsed to set a job as stalled increased from 60s to 240s
  - correct bug in job_task. Celery worker does not release session if a task raise an Exception

## Version 1.5.0 (2019-09-04)

Rilascio nuove funzionalità
* Added
  - added methods expunge, pre_expunge e post_expunge to ApiObject
  - added methods base_stmp2 and run2 in PaginatedQueryGenerator
  - added logger elk for api and task
  - added microsecond to event stored in mysql db
  - added signature Celery that register task in redis when uuid is generated from the apply_async
  - added send of log item for the api class to elasticsearch if it is configured
* Fixed
  - modify max query window for event to 2 hours
  - changed wait_for_job_complete. Timeout that identify a job as stalled is increased from 60s to 240s

## Version 1.4.0 (2019-05-24)

Rilascio nuove funzionalità
* Added
  - added field provider in the class classe common.model.authorization.User to indicate the autentication provider
  - added management of the field provider in the api of auth.user
* Fixed
  - revision of method user_request
  - modified query api of domains in query api of providers
  - modified configuration of the authentication provider ldap
  - map[update of the method get_entity signature:inserted params *args, **kvargs]
  - map[Class GetAllTasksRequestSchema:corrected error in swagger validation, removed the parameter missing=None for the field type]
  - modified behaviour of the methid AbstractDbManager.add_perm_tag. Removed the rollback when permtag already exixsts

## Version 1.3.0 (2019-02-27)

Rilascio nuove funzionalità
* Added
  - added runner to realize concurrent test unit
* Fixed
  - increased the size to 500 chars of the field desc in table event

## Version 1.2.0 (2019-02-01)

Rilascio nuove funzionalità
* Added
  - BeehiveApiClient added method set_ssh_group_authorization
* Fixed
  - corrected bug in class PaginatedQueryGenerator that block change of group by filter

## Version 1.1.0 (2019-01-13)

Rilascio nuove funzionalità
* Added
  - added invoked job reference in caller task
* Fixed
  - map[trace:changed event trace. It was printed the name of the traced method]
  - map[event:revision of the list query. It is too slow. Query was limited to one day.]
  - map[auth:revision of the method that control user has a specific role]

## Version 1.0.0 (2018-07-31)

Rilascio nuove funzionalità

## Version 0.1.0 (2016-04-18)

Rilascio nuove funzionalità
