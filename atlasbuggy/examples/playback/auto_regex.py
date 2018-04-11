import string
import random
from atlasbuggy import Orchestrator, Message
from atlasbuggy.log import PlaybackNode

class MyMessage(Message):
    def __init__(self, n, timestamp=None):
        super(MyMessage, self).__init__(n)

        self.prop1 = 0
        self.prop2 = 0.0
        self.prop3 = ""

        str_serialization, regex_serialization, message_data_types = self.auto_serialize()

        print("str_serialization:", str_serialization)
        print("regex_serialization:", regex_serialization)
        print("message_data_types:", message_data_types)
        print("\n")


class TestMessage1(Message):
    def __init__(self, n, timestamp=None):
        super(TestMessage1, self).__init__(n)

        self.prop1 = 0
        self.prop2 = 0.0
        self.prop3 = ""

        self.auto_serialize()


class TestMessage2(Message):
    def __init__(self, n, timestamp=None):
        super(TestMessage2, self).__init__(n, timestamp)

        self.prop_a = 0
        self.prop_b = 0.0
        self.prop_c = ""
        self.prop_d = [0, 0, 0]

        self.auto_serialize()


if __name__ == '__main__':
    def test_message_equality():
        print("\n\n----- Message parse equality tests -----\n")
        message = MyMessage(0)
        message_str = str(message)
        print(message_str)

        parsed_message = MyMessage.parse(message_str)

        print("parsed message: ", parsed_message)
        assert message == parsed_message, "parsed message and original message don't match!!"
        print("messages match!\n\n")


    def random_str(N):
        return ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(N))


    def test_message_pointers():
        print("\n\n----- Message pointer tests -----\n")
        num_messages = 10
        message_1s = [TestMessage1(n) for n in range(num_messages)]
        message_2s = [TestMessage2(n) for n in range(num_messages)]

        for m1 in message_1s:
            m1.prop1 = random.randint(0, 255)
            m1.prop2 = random.random()
            m1.prop3 = random_str(m1.prop1)

        for m2 in message_2s:
            m2.prop_c = random_str(m2.prop_a)
            m2.prop_d = [random.randint(0, 63) for _ in range(3)]

        assert_message = "Original property '%s' of type Message has been tampered!"
        assert Message.str_serialization == "%s(t=%s, n=%s)", assert_message % "str_serialization "
        assert Message.message_regex == r"", assert_message % "message_regex "
        assert Message.message_data_types == tuple(), assert_message % "message_data_types "
        assert Message.float_regex == r"([-+]?(?:(?:\d*\.\d+)|(?:\d+\.?))(?:[Ee][+-]?\d+)?)", assert_message % "float_regex "
        assert Message.int_regex == r"([-+]?[0-9]+)", assert_message % "int_regex "
        assert Message.str_regex == r"\'(.*?)\'", assert_message % "str_regex "
        assert Message.ignored_properties == ["n", "timestamp", "is_auto_serialized", "ignored_properties"], assert_message % "ignored_properties "

        print("Original Message class preserved")

        for index in range(1, num_messages):
            assert message_1s[0] is not message_1s[index], "Message type 1 #%s points to the first index!" % index
            assert message_1s[0] != message_1s[index], "Message type 1 #%s is equal to the first index!" % index

        for index in range(1, num_messages):
            assert message_2s[0] is not message_2s[index], "Message type 2 #%s points to the first index!" % index
            assert message_2s[0] != message_2s[index], "Message type 2 #%s is equal to the first index!" % index

        print("All messages are independent")

        for index in range(num_messages):
            assert message_1s[index] != message_2s[index], "Index #%s doesn't match!"
        print("Inequality test passed")

        message_2s_copy = []
        for m2 in message_2s:
            message_2s_copy.append(m2.copy())

        for index in range(num_messages):
            assert message_2s_copy[index] == message_2s[
                index], "Values from copied message #%s don't match original!" % index
            assert message_2s_copy[index] is not message_2s[
                index], "Didn't actually copy the values from index #%s. Pointers match!" % index

        for index in range(num_messages):
            message_2s_copy[index].prop_a += 1

        for index in range(num_messages):
            assert message_2s_copy[index] != message_2s[
                index], "Values from copied message #%s match original after being changed!" % index

        print("Copy test passed")


    test_message_equality()
    test_message_pointers()
