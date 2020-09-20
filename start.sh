# intended to be started through crontab on raspberry pi:
# * * * * * cd /home/pi/smartguard && bash start.sh > start.log

if pgrep -x "python" > /dev/null
then
    echo "Smartguard is already  running. Skipping."
else
    source /home/pi/opencv_course/venv/bin/activate
    cd /home/pi/smartguard
    export PYTHONPATH="."
    export PYTHONUNBUFFERED=1
    python device/start.py > smartguard.log 2> smartguard.log &
    echo "Started smartguard. Exit code: $?"
fi