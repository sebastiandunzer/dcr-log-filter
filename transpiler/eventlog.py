# coding=utf-8
"""The module implements a data structure to represent an event log"""
import opyenxes.data_in.XesXmlParser as XESParser
import opyenxes.model.XAttributable as xA


class EventLog(object):
    """ Represents a whole event log """

    event_log = None

    def __init__(self):
        """
        Default constructor for a whole event log
        """
        self.Traces = []

    def append_trace(self, trace):
        """
        Appends a trace to the event log from the XES file
        :param trace: the trace that is added
        """
        self.Traces.append(trace)

    def print_event_log(self):
        """
        Is used to print the log for test purposes
        :return: None
        """
        for trace in self.Traces:
            print("In Trace {} there are {} Events: \n ".format(self.Traces.index(trace), len(trace.Events)))
            for event in trace.Events:
                print("     Event Info|| Event Name: {}      Event Role: {}     Time_stamp: {}".format(
                    event.EventName, event.Role, event.Timestamp))

    @staticmethod
    def create_event_log_xes(handler: XESParser):
        """
        static method to create the whole event log
        :param handler: opyenxes file handler
        :return: event log
        """
        event_log = EventLog()
        trace_list = handler[0]
        set_trace_id = False
        trace_id = 0
        for trace in trace_list:
            try:
                tr_attributes: xA = trace.get_attributes()
                if 'concept:name' in tr_attributes:
                    trace_id = tr_attributes.get('concept:name').get_value()
                    set_trace_id = True
            except:
                pass
            trace_tmp = Trace(trace_id)
            trace_tmp.add_trace_data(trace.get_attributes())
            if not set_trace_id:
                trace_id += 1
            for event in trace:
                # get the attributes for an event
                attributes: xA = event.get_attributes()
                event_timestamp = None
                event_name = str()
                event_role = str()
                if 'concept:name' in attributes:
                    event_name = attributes.get('concept:name').get_value()
                    attributes.pop('concept:name', None)
                # get role from event log
                if 'org:role' in attributes:
                    event_role = attributes.get('org:role').get_value()
                    attributes.pop('org:role', None)
                elif 'org:resource' in attributes:
                    event_role = attributes.get('org:resource').get_value()
                    attributes.pop('org:resource', None)

                # add time to event log
                if 'time:timestamp' in attributes:
                    event_timestamp = attributes.get('time:timestamp').get_value()
                    attributes.pop('time:timestamp', None)

                event_tmp = Event(event_name, event_role, event_timestamp, attributes)
                trace_tmp.append_event(event_tmp)
            # append the event to the trace
            event_log.append_trace(trace_tmp)
        return event_log


class Event(object):
    """
    The event class that represents an atomic event
    """

    def __init__(self, event_name, event_role, time_stamp, attributes=None):
        """
        Default constructor of the Event class
        """
        self.EventName = event_name
        self.Role = event_role
        self.Timestamp = time_stamp
        self.Attributes = attributes


class Trace(object):
    """
    Represents a trace of a log
    """

    def __init__(self, trace_id):
        """
        Default constructor of a Trace, a trace is a set of related events often also called a case
        a case is the instance of one process at a time
        """
        self.Events = []
        self.TraceId = trace_id
        self.TraceData = {}

    def append_event(self, event):
        """
        Append an event to the log trace
        :param event: The event that is added to the log trace
        :return:
        """
        self.Events.append(event)

    def add_trace_data(self, data):
        self.TraceData = data

