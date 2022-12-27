#!/bin/bash
# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

source $1/bin/activate
$1bin/$2 $3
deactivate