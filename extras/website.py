import os
import logging
from flask import Flask, render_template
from atlasbuggy.datastream import ThreadedStream, DataStream


class Website(ThreadedStream):
    """
    Base class for flask based website hosts. This class should be subclassed
    """
    def __init__(self, template_folder, static_folder, flask_params=None, app_params=None, enabled=True, log_level=None,
                 name=None, use_index=True, host='0.0.0.0', port=5000):
        super(Website, self).__init__(enabled, name, log_level)

        if flask_params is None:
            flask_params = {}

        self.flask_logger = logging.getLogger('werkzeug')

        template_folder = os.path.abspath(template_folder)
        static_folder = os.path.abspath(static_folder)

        self.host = host
        self.port = port

        self.app = Flask(__name__, template_folder=template_folder, static_folder=static_folder, **flask_params)

        self.flask_logger.setLevel(logging.DEBUG)
        self.flask_logger.addHandler(self.print_handle)
        if DataStream._log_info["file_handle"] is not None:
            self.flask_logger.addHandler(DataStream._log_info["file_handle"])

        if use_index:
            self.app.add_url_rule("/", "index", self.index)

        if app_params is not None:
            self.app_params = app_params
        else:
            self.app_params = {}

        self.flask_logger.setLevel(logging.DEBUG)

        self.set_to_daemon()

    def index(self):
        """
        app.add_url_rule('/', 'hello', hello_world)

        Is the same as:

        @app.route('/hello')
        def hello_world():
           return 'hello world'
        
        Override this method as needed
        """
        return render_template('index.html')

    def run(self):
        """
        Do not override this method. Starts the website.
        """
        self.logger.debug("Running website on %s:%s" % (self.host, self.port))
        try:
            self.app.run(host=self.host, port=self.port, debug=False, threaded=True, **self.app_params)
        except BaseException as error:
            self.logger.debug("Website stopped running...")
            self.logger.exception(error)
            raise
