-- SPDX-License-Identifier: GPL-3.0-or-later
--
-- (C) Copyright 2018-2019 CSI-Piemonte

ALTER TABLE perm_tag ADD INDEX(value);
ALTER TABLE perm_tag_entity ADD INDEX(entity);
ALTER TABLE perm_tag_entity ADD INDEX(tag);
ALTER TABLE `event` ADD INDEX(creation);
-- ALTER TABLE `event` ADD INDEX(data);