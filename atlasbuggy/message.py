import re
import copy
import time
import inspect


class Message:
    str_serialization = "%s(t=%s, n=%s)"
    message_regex = r""
    message_data_types = tuple()
    float_regex = r"([-+]?(?:(?:\d*\.\d+)|(?:\d+\.?))(?:[Ee][+-]?\d+)?)"
    int_regex = r"([-+]?[0-9]+)"
    str_regex = r"\'(.*?)\'"

    ignored_properties = ["n", "timestamp"]

    def __init__(self, n, timestamp=None):
        if timestamp is None:
            self.timestamp = time.time()
        else:
            self.timestamp = timestamp
        self.n = n

        init_signature = tuple(inspect.signature(self.__init__).parameters.keys())
        if init_signature != ("n", "timestamp"):
            raise ValueError("Message classes must have init parameters (n, timestamp=None)! "
                             "This message has the signature: %s" % str(init_signature))

    @classmethod
    def parse(cls, message):
        match = re.match(cls.message_regex, message)
        if match is not None:
            n = int(match.group(1))
            message_time = float(match.group(2))
            new_message = cls(message_time, n)

            groups = match.groups()[2:]

            for index in range(0, len(groups), 2):
                group_name = groups[index]
                group_value = groups[index + 1]
                group_type = cls.message_data_types[index // 2]

                value = group_type(group_value)

                setattr(new_message, group_name, value)

            return new_message
        else:
            return None

    def get_message_props(self):
        properties_table = copy.deepcopy(self.__dict__)
        for ignored_property in self.ignored_properties:
            properties_table.pop(ignored_property)

        return properties_table

    def get_serialization(self):
        properties_table = self.get_message_props()
        properties_table = list(properties_table.items())
        properties_table.sort(key=lambda p: p[0])
        properties_table = [str(item) for sublist in properties_table for item in sublist]

        serialization_props = [self.name, self.n, self.timestamp]
        serialization_props.extend(properties_table)

        return self.__class__.str_serialization % tuple(serialization_props)

    @classmethod
    def ignore_prop_named(cls, property_name):
        cls.ignored_properties.append(property_name)

    def auto_serialize(self):
        str_serialization = "%s(n=%s, t=%s"
        regex_serialization = r"%s\(n=%s, t=%s" % (self.name, self.int_regex, self.float_regex)

        properties_table = self.get_message_props()

        properties_table = list(properties_table.items())
        properties_table.sort(key=lambda p: p[0])  # properties will always be in alphabetical order

        message_data_types = []

        for index, (name, value) in enumerate(properties_table):
            str_serialization += ", %s='%s'"
            regex_serialization += r", (%s)=" % name
            if type(value) == int:
                regex_serialization += r"\'%s\'" % self.int_regex
                message_data_types.append(int)

            elif type(value) == float:
                regex_serialization += r"\'%s\'" % self.float_regex
                message_data_types.append(float)

            else:
                # if this is the last item, match the string until ")" instead of ","
                regex_serialization += r"%s" % self.str_regex
                message_data_types.append(str)

        str_serialization += ")"
        regex_serialization += r"\)"
        message_data_types = tuple(message_data_types)

        self.__class__.str_serialization = str_serialization
        self.__class__.message_regex = regex_serialization
        self.__class__.message_data_types = message_data_types

        return str_serialization, regex_serialization, message_data_types

    @property
    def name(self):
        return self.__class__.__name__

    def copy(self):
        new_message = self.__class__(self.n, self.timestamp)
        for name, value in self.get_message_props().items():
            new_message.__dict__[name] = copy.deepcopy(value)

        return new_message

    def __eq__(self, other):
        if isinstance(other, type(self)):
            return other.get_message_props() == self.get_message_props()
        else:
            return False

    def __str__(self):
        return self.get_serialization()
