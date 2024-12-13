/*
  SPDX-License-Identifier: EUPL-1.2

  (C) Copyright 2018-2024 CSI-Piemonte
*/
-- get Apimethod type id
set @tipo=(select id from sysobject_type st  where objtype  = 'service' and objdef = 'ApiMethod');


SELECT  @tipo;

-- get susysonject for "*" Apimethod
set @objall=(SELECT s.id from sysobject s  WHERE  s.type_id =@tipo and objid  = '*');

SELECT  @objall

-- get permsion for "*"  on "*" Apimethod
set @perm=(select sp.id from sysobject_permission sp  where sp.obj_id= @objall and sp.action_id =1);

 select @perm;

;

INSERT INTO role_permission (role_id, permission_id)
select r.id, @perm -- , r.name
from
	`role` r
	left outer join  role_permission rp  on rp.role_id  = r.id and rp.permission_id  = @perm
where
	rp.id  is null and
	(r.name like '%Admin%' or r.name like '%Viewer%' );

	name like 'DivAdminRole%' or
	name like 'AccountViewerRole%' or
	name like 'AccountAdminRole%' or
	name like 'OrgViewerRole%' or
	name like 'OrgOperatorRole%' ;
