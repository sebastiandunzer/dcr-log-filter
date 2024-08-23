# coding=utf-8
"""
The module contains the conformance data informations
"""
import threading


class RuleViolation(object):
    """
    The overall conformance analysis data contains information about all failed traces in an event log in an aggregated
    form
    """
    analysis_data = None

    def __init__(self):
        """
        Default initializer
        """
        self.ViolatingTraceIDs = []
        self.ViolatingTraces = []
        self.ConformantTraces = []
        self.ConformantTraceIDs = []
        self.Lock = threading.RLock()  # Used to make the class thread safe
        RuleViolation.analysis_data = self

    def create_violated_traces_dict(self):
        """
        Creates a dict from the Violating traces
        :return: a dict with the process paths
        """
        process_paths = {}
        for trace in self.ViolatingTraces:
            process_path = str()
            for event in trace.Events:
                process_path += "  -{}".format(event.EventName)
            process_path = process_path.lstrip()[1:]
            if process_path in process_paths:
                process_paths[process_path] += 1
            else:
                process_paths[process_path] = 1
        return process_paths

    def append_conformance_data(self, trace, violated):
        """
        Thread safe method to add trace conformance analysis data to the overall conformance analysis data
        :type trace_conformance_data: TraceConformanceAnalysisData that will be added to the overall information
        """
        # Acquire lock for thread safe execution
        self.Lock.acquire()

        if violated:
            self.ViolatingTraces.append(trace)
            self.ViolatingTraceIDs.append(trace.TraceId)
        else:
            self.ConformantTraces.append(trace)
            self.ConformantTraceIDs.append(trace.TraceId)


        # Release lock for next thread
        self.Lock.release()

