source /home/pi/opencv_course/venv/bin/activate
cd /home/pi/smartguard
export PYTHONPATH="."
export PYTHONUNBUFFERED=1
python device/start.py > smartguard.log 2> smartguard.log &
echo "exit code: "
echo $?
