# coding=utf-8
"""
This module is used to parse an event log and afterwards bring it to the data structure contained in ``eventlog.py``
"""
import opyenxes.data_in.XesXmlParser as XesParser

from eventlog import EventLog


def get_event_log(file_path: str = None):
    """
    Gets the event log data structure from the event log file.
    Dispatches the methods to be used by file tyoe
    :param use_celonis: If the attribute is set to true the event log will be retrieved from celonis
    :param file_path: Path to the event-log file
    :return:EventLog data structure
    """
    if file_path is None:
        raise ValueError("Parameters file_path was None and use_celonis was false at the same time."
                         "This behavior is not supported")
    file_path_lowercase = file_path.lower()
    if file_path_lowercase.endswith(".xes"):
        return __handle_xes_file(file_path)
    else:
        raise ValueError('The input file was not a XES file')


def __handle_xes_file(import_path):
    """
    Puts an xes file into a common data structure
    :param import_path: Path to the xes file
    :return: Void
    """
    opyenxes_log = __import_event_log_xes(import_path)
    return EventLog.create_event_log_xes(opyenxes_log)


def __import_event_log_xes(import_path):
    """
    Import an event log from an xes file
    :param import_path: Path of the event log
    :return: parsed event log
    """
    xml_parser = XesParser.XesXmlParser()
    can_parse = xml_parser.can_parse(import_path)
    if can_parse:
        parsed_log = xml_parser.parse(import_path)
    else:
        raise Exception("Error: Xes-file {} cannot be parsed".format(import_path))
    return parsed_log
