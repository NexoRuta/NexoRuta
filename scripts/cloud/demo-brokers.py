#!/usr/bin/env python3
"""Start isolated free local brokers and the existing Kafka worker for the synthetic demo."""
import importlib.util,json,os,pathlib,subprocess,sys,time,secrets,signal
ROOT=pathlib.Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('nexoruta_cloud_dev',ROOT/'scripts/cloud/dev.py');dev=importlib.util.module_from_spec(spec);spec.loader.exec_module(dev)
s=dev.load();label='nexoruta.demo='+s['database']
def run(args,**kw):return subprocess.run(args,check=True,**kw)
def container(name,image,args,environment=None):
 found=subprocess.run(['docker','inspect',name],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 if found.returncode==0:
  owner=subprocess.check_output(['docker','inspect','-f','{{index .Config.Labels "nexoruta.demo"}}',name],text=True).strip()
  if owner!=s['database']:raise RuntimeError('Container belongs to another checkout')
  run(['docker','start',name],stdout=subprocess.DEVNULL)
 else:run(['docker','run','-d','--name',name,'--label',label,*args,image],stdout=subprocess.DEVNULL,env=environment)
if sys.argv[1:]==['stop']:
 for file in ['demo-kafka-worker.pid','demo-rabbit-worker.pid']:
  record=dev.STATE/file
  if not record.exists():continue
  pidvalue=int(record.read_text());command=pathlib.Path(f'/proc/{pidvalue}/cmdline')
  if command.exists() and command.read_bytes():
   if b'NexoRuta.Worker.dll' not in command.read_bytes() or str(ROOT).encode() not in command.read_bytes():raise RuntimeError('PID does not belong to this checkout worker')
   os.kill(pidvalue,signal.SIGTERM)
   for _ in range(50):
    if not command.exists() or not command.read_bytes():break
    time.sleep(.1)
   else:raise RuntimeError('Worker did not stop')
  record.unlink()
 print('Workers propios detenidos; brokers y datos conservados.');raise SystemExit(0)
if sys.argv[1:]!=['start']:raise SystemExit('Uso: demo-brokers.py start | stop')
for file in ['demo-kafka-worker.pid','demo-rabbit-worker.pid']:
 record=dev.STATE/file
 if record.exists():
  command=pathlib.Path('/proc/'+record.read_text().strip()+'/cmdline')
  if command.exists() and command.read_bytes():raise RuntimeError('Stop this demo worker before rebuilding it')
worker_artifacts=dev.STATE/'demo-worker-artifacts'
run(['dotnet','build',str(ROOT/'backend/src/NexoRuta.Worker'),'--artifacts-path',str(worker_artifacts),'--nologo'],cwd=ROOT)
worker_dll=worker_artifacts/'bin/NexoRuta.Worker/debug/NexoRuta.Worker.dll'
container('nexoruta-demo-kafka-3141','confluentinc/cp-kafka:7.9.10',[
 '-p','127.0.0.1:19092:9094',
 '-e','CLUSTER_ID=TkVYT1JVVEFfTE9DQUxfMQ','-e','KAFKA_NODE_ID=1','-e','KAFKA_PROCESS_ROLES=broker,controller',
 '-e','KAFKA_CONTROLLER_QUORUM_VOTERS=1@localhost:9093','-e','KAFKA_CONTROLLER_LISTENER_NAMES=CONTROLLER',
 '-e','KAFKA_LISTENER_SECURITY_PROTOCOL_MAP=INTERNAL:PLAINTEXT,EXTERNAL:PLAINTEXT,CONTROLLER:PLAINTEXT',
 '-e','KAFKA_LISTENERS=INTERNAL://0.0.0.0:9092,EXTERNAL://0.0.0.0:9094,CONTROLLER://0.0.0.0:9093',
 '-e','KAFKA_ADVERTISED_LISTENERS=INTERNAL://localhost:9092,EXTERNAL://127.0.0.1:19092','-e','KAFKA_INTER_BROKER_LISTENER_NAME=INTERNAL',
 '-e','KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR=1','-e','KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR=1','-e','KAFKA_TRANSACTION_STATE_LOG_MIN_ISR=1','-e','KAFKA_MIN_INSYNC_REPLICAS=1','-e','KAFKA_AUTO_CREATE_TOPICS_ENABLE=false','-e','KAFKA_HEAP_OPTS=-Xms256m -Xmx512m'])
if 'demoRabbitPassword' not in s:
 s['demoRabbitPassword']=secrets.token_hex(24);(dev.STATE/'private.json').write_text(json.dumps(s));(dev.STATE/'private.json').chmod(0o600)
rabbitenv=dict(os.environ,RABBITMQ_DEFAULT_USER='nexoruta_demo',RABBITMQ_DEFAULT_PASS=s['demoRabbitPassword'])
container('nexoruta-demo-rabbit-3141','rabbitmq:4-management',['-p','127.0.0.1:15672:5672','-e','RABBITMQ_DEFAULT_USER','-e','RABBITMQ_DEFAULT_PASS'],rabbitenv)
container('nexoruta-demo-mongo-3141' ,'mongo:8.0',['-p','127.0.0.1:27018:27017'])
for _ in range(60):
 ready=subprocess.run(['docker','exec','nexoruta-demo-kafka-3141','kafka-topics','--bootstrap-server','localhost:9092','--list'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 if ready.returncode==0:break
 time.sleep(1)
else:raise RuntimeError('Synthetic Kafka not ready')
for topic in ['nexoruta.envios.creados.v1','nexoruta.password-recovery.requested.v1','nexoruta.comercios.v2']:
 run(['docker','exec','nexoruta-demo-kafka-3141','kafka-topics','--bootstrap-server','localhost:9092','--create','--if-not-exists','--topic',topic,'--partitions','3','--replication-factor','1'],stdout=subprocess.DEVNULL)
pid=dev.STATE/'demo-kafka-worker.pid'
if pid.exists() and pathlib.Path('/proc/'+pid.read_text().strip()+'/cmdline').exists() and pathlib.Path('/proc/'+pid.read_text().strip()+'/cmdline').read_bytes():raise RuntimeError('Demo worker already running')
e=dev.env(s,'worker');e.update(Messaging__Transport='Kafka',Kafka__BootstrapServers='127.0.0.1:19092',MongoDb__ConnectionString='mongodb://127.0.0.1:27018',MongoDb__Database='nexoruta_demo_3141',MongoDb__PasswordRecoveryCollection='PasswordRecoveryRequested')
log=open(dev.STATE/'demo-kafka-worker.log','ab',buffering=0)
process=subprocess.Popen(['dotnet',str(worker_dll)],cwd=ROOT/'backend/src/NexoRuta.Worker',env=e,stdout=log,stderr=log,start_new_session=True)
pid.write_text(str(process.pid))
rpid=dev.STATE/'demo-rabbit-worker.pid'
if not rpid.exists() or not pathlib.Path('/proc/'+rpid.read_text().strip()+'/cmdline').exists() or not pathlib.Path('/proc/'+rpid.read_text().strip()+'/cmdline').read_bytes():
 re=dev.env(s,'worker');re.update(Messaging__Transport='RabbitMq',RabbitMq__Host='127.0.0.1',RabbitMq__Port='15672',RabbitMq__Username='nexoruta_demo',RabbitMq__Password=s['demoRabbitPassword'],Email__Smtp__Host='127.0.0.1',Email__Smtp__Port='11025',Email__Smtp__FromAddress='nexoruta@demo.example.test')
 rlog=open(dev.STATE/'demo-rabbit-worker.log','ab',buffering=0)
 rp=subprocess.Popen(['dotnet',str(worker_dll)],cwd=ROOT/'backend/src/NexoRuta.Worker',env=re,stdout=rlog,stderr=rlog,start_new_session=True);rpid.write_text(str(rp.pid))
print('Kafka, Mongo y Worker aislados iniciados; revisar la bandeja de avisos de Commerce.')
