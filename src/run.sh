# use uvnicor to start app in current folder
#how to run local main with watch
sudo service postgresql start
export PYTHONPATH=$PYTHONPATH:/mnt/d/Github/MetaAgent/instructor
uvicorn main:app --host 0.0.0.0 --port 8300  --reload --reload-dir ./
# uvicorn main:app --host 0.0.0.0 --port 8300