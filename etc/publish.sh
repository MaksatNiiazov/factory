#!/bin/bash

set -e

# для режима --ci некоторые этапы упрощены
# --patch самый быстрый для наката фикса мгновенного (без дампа итд)

if [[ $1 == "--ci" ]]; then
    IS_CI=true
    IS_PATCH=false
    echo -e "\033[1m[CI PUBLISH MODE]\033[0m"
elif [[ $1 == "--patch" ]]; then
	# все упрощения для IS_CI нужны + ещё флаг
	IS_CI=true
	IS_PATCH=true
	echo -e "\033[1m[FAST PATCH PUBLISH MODE]\033[0m"
else
    IS_CI=false
    IS_PATCH=false
    echo -e "\033[1m[FULL PUBLISH MODE]\033[0m"
fi

# чтобы сравнить не изменилось ли (только в быстрых режимах)
if $IS_CI; then
	REQUIREMENTS_PREV_MD5=`md5sum ${OPS_ROOT}/etc/requirements.txt`
else
	REQUIREMENTS_PREV_MD5="alwaysdo"
fi

echo -e "\033[1mSTOP SERVICES...\033[0m"
sudo -E "${OPS_ROOT}/etc/stop.sh"

echo -e "\033[1mBACKUP...\033[0m"
if ! $IS_PATCH; then
	${OPS_ROOT}/etc/backup.sh
else
	echo "(skip)"
fi

echo -e "\033[1mACTIVATE...\033[0m"
. ${OPS_ROOT}/env/bin/activate

echo -e "\033[1mGIT PULL...\033[0m"
git -C ${OPS_ROOT} pull

echo -e "\033[1mPIP INSTALL...\033[0m"
REQUIREMENTS_NEW_MD5=`md5sum ${OPS_ROOT}/etc/requirements.txt`
if [[ $REQUIREMENTS_PREV_MD5 == $REQUIREMENTS_NEW_MD5 ]]; then
	echo "(requirements.txt not changed)"
else
    pip install -r ${OPS_ROOT}/etc/requirements.txt
fi

echo -e "\033[1mDJANGO MIGRATE...\033[0m"
${OPS_ROOT}/app/manage.py migrate

echo -e "\033[1mDJANGO COLLECTSTATIC...\033[0m"
${OPS_ROOT}/app/manage.py collectstatic --noinput

echo -e "\033[1mDJANGO COMPILEMESSAGES...\033[0m"
${OPS_ROOT}/app/manage.py compilemessages

echo -e "\033[1mROTATE LOGS...\033[0m"
${OPS_ROOT}/etc/rotatelogs.sh

echo -e "\033[1mRESTART SERVICES...\033[0m"
if $IS_CI; then
	echo "(soft restart)"
	sudo -E ${OPS_ROOT}/etc/restart.sh soft
else
	sudo -E ${OPS_ROOT}/etc/restart.sh
fi

echo -e "\033[1mRUN TESTS...\033[0m"
#${OPS_ROOT}/app/manage.py test ${OPS_ROOT}/app/ --settings=project.test_settings

echo -e "\033[1mOK\033[0m"
