#!/usr/bin/env bash
startdir=$(pwd)
appdir=$(dirname "${0}")

cd "${appdir}"
[ -d "${appdir}}/dist" ] && rm -rf "${appdir}/dist"
build_venv=$(mktemp -d -t venv-)
echo "[INFO] Creating python virtual environment in \"${build_venv}\""
python3.12 -m venv "${build_venv}" \
&& . "${build_venv}/bin/activate" \
&& echo "[INFO] Installing python modules" \
&& python3 -m pip install --upgrade -r requirements.txt 2>&1 > build.log \
&& echo "[INFO] Building application" \
&& python3 setup.py py2app 2>&1 >> build.log \
&& echo "[INFO] Build Completed. The Application has been saved in \"${appdir}/dist\"" \
&& deactivate

[ -d "${build_venv}" ] && rm -rf "${build_venv}"
[ -d "${appdir}/build" ] && rm -rf "${appdir}/build"
cd "${startdir}"
