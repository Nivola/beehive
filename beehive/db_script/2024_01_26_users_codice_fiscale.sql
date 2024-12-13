/*
  SPDX-License-Identifier: EUPL-1.2

  (C) Copyright 2018-2024 CSI-Piemonte
*/
ALTER TABLE auth.user
ADD COLUMN `taxcode` VARCHAR(16),
ADD COLUMN `ldap` VARCHAR(100)
;

UPDATE auth.user
SET ldap = email
WHERE email LIKE '%@csi.it'
OR email LIKE '%@fornitori.nivola'
