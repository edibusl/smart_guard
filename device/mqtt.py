from typing import Optional, List, Callable
import logging
import json

from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient

from device.singleton import Singleton


class Mqtt(metaclass=Singleton):
    OnMessageCallback = Callable[[str, dict], None]

    def __init__(self):
        self.port: Optional[int] = None
        self.host: Optional[str] = None
        self.thing_name: Optional[str] = None
        self.client_id: Optional[str] = None
        self.root_ca_path: Optional[str] = None
        self.certificate_path: Optional[str] = None
        self.private_key_path: Optional[str] = None
        self.myAWSIoTMQTTClient: Optional[AWSIoTMQTTClient] = None
        self.topic: Optional[str] = None
        self.callbacks: List[Mqtt.OnMessageCallback] = []

        self._init_loggers()

    def _init_loggers(self):
        # # Configure logging
        # iotcore_logger = logging.getLogger("AWSIoTPythonSDK.core")
        # iotcore_logger.setLevel(logging.DEBUG)
        # stream_handler = logging.StreamHandler()
        # stream_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        # iotcore_logger.addHandler(stream_handler)

        self.logger = logging.getLogger(__name__)

    def connect(self, configs):
        # TODO - Configs should be initialized from "configs" argument
        certs_dir = "device/certs"
        self.port = 8883
        self.host = "a21uta8yahkocj-ats.iot.us-east-1.amazonaws.com"
        self.thing_name = "raspberrypi_edi"
        self.client_id = "basicPubSub"  # clientId should be permitted in the Thing's policy
        self.root_ca_path = f"{certs_dir}/root-CA.crt"
        self.certificate_path = f"{certs_dir}/{self.thing_name}.cert.pem"
        self.private_key_path = f"{certs_dir}/{self.thing_name}.private.key"
        self.topic = configs['topic']

        # Init AWSIoTMQTTClient
        self.myAWSIoTMQTTClient = AWSIoTMQTTClient(self.client_id)
        self.myAWSIoTMQTTClient.configureEndpoint(self.host, self.port)
        self.myAWSIoTMQTTClient.configureCredentials(self.root_ca_path, self.private_key_path, self.certificate_path)

        # AWSIoTMQTTClient connection configuration
        self.myAWSIoTMQTTClient.configureAutoReconnectBackoffTime(1, 32, 20)
        self.myAWSIoTMQTTClient.configureOfflinePublishQueueing(-1)  # Infinite offline Publish queueing
        self.myAWSIoTMQTTClient.configureDrainingFrequency(2)  # Draining: 2 Hz
        self.myAWSIoTMQTTClient.configureConnectDisconnectTimeout(10)  # 10 sec
        self.myAWSIoTMQTTClient.configureMQTTOperationTimeout(5)  # 5 sec

        # Connect and subscribe to AWS IoT
        self.myAWSIoTMQTTClient.connect()

        # Subscribe to topics
        self.logger.info(f"Subscribing to topic {self.topic}")
        self.myAWSIoTMQTTClient.subscribe(self.topic, 1, self._callback)

    def register_callback(self, callback: OnMessageCallback):
        self.callbacks.append(callback)

    def _callback(self, client, userdata, message):
        self.logger.info(f"Received a new message on topic {message.topic}: {message.payload}")

        msg_dict = json.loads(message.payload)
        for callback in self.callbacks:
            callback(message.topic, msg_dict)

    def send(self, topic, msg):
        message_json = json.dumps(msg)
        self.myAWSIoTMQTTClient.publish(topic, message_json, 1)
        self.logger.info(f'Published topic "{topic}": {message_json}\n')
