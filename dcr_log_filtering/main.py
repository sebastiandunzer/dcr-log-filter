# coding=utf-8
"""The main file of the dcr-cc that is executed"""
from threading import Thread

import os.path
import pickle
import time

import cmd_parser
import eventlog_parser
from result_data import RuleViolation
from graph import DCRGraph
from marking import Marking
from xml.etree import ElementTree as Etree

import pm4py.discovery as discovery
import pm4py.objects.log.importer as xes_importer
import pm4py.visualization.petri_net as vis_factory



miners = {
    'inductive': discovery.discover_petri_net_inductive
}

def main():
    """
    Program main method starts by parsing the DCR graph afterwards retrieving the Event Log
    subsequently the conformance is checked
    :return:
    """
    global dcr_graph

    args = cmd_parser.parse_args()
    data_path = args.eventLog
    out_path = args.outFile
    xml_path = args.XmlDcr
    ns = args.namespace
    dcr_graph = None
    import_successful = False

    name = xml_path.split('/')[-1].split('.')[0]
    name_tau_v = name + "_tauv.txt"
    path_tau_v = f"Resources/pickle/{name_tau_v}"
    tau_v = []


    if os.path.exists(path_tau_v):
        with open(path_tau_v, "rb") as f:
            tau_v = pickle.load(f)
        import_successful = True

    if not import_successful:
        start_time = time.clock()
        tau_v = perform_rule_checking(data_path, xml_path)
        with open(path_tau_v, "wb") as f:
            pickle.dump(tau_v, f)
        end_time = time.clock()
        print(f"Conformance calculation took: {end_time-start_time}")
        print(len(tau_v))

    if not os.path.exists(out_path) and tau_v:
        filter_event_log(data_path, out_path, tau_v, ns)

    discover(out_path, name)


def perform_rule_checking(data_path, xml_path):
    global dcr_graph
    dcr_graph = DCRGraph.get_graph_instance(xml_path)
    event_log = eventlog_parser.get_event_log(data_path)
    ca = RuleViolation()
    # if parallel is set: code is executed in thread pool
    parallel = False


    if parallel:
        threads = []
        for trace in event_log.Traces:
            t = Thread(target=rule_checking, args=(trace, ca))
            threads.append(t)
        for t in threads:
            t.start()
        for t in threads:
            t.join()
    else:
        for trace in event_log.Traces:
            rule_checking(trace,ca)
    # If fitness information is desired uncomment:
    # create_conformance_output(ca, event_log)
    return ca.ViolatingTraceIDs


def create_conformance_output(ca, event_log):
    """
    Creates the console output of the program
    :param ca:
    :param event_log:
    :return:
    """
    if len(ca.ViolatingTraces) > 0:
        # Calculate ratios and replay fitness, Round up to two digits
        violating_case_ratio = len(ca.ViolatingTraces) / len(event_log.Traces)
        replay_fitness = 1 - violating_case_ratio
        replay_fitness = "%.2f" % replay_fitness
        violating_case_ratio *= 100
        violating_case_ratio = "%.2f" % violating_case_ratio
        conformance_ratio = 100 - float(violating_case_ratio)

        sorted_violated_cases = sorted(ca.create_violated_traces_dict().items(), key=lambda kv: kv[1], reverse=True)

        # Print all detailed information
        print("\n{} process paths failed the events\n".format(len(sorted_violated_cases)))
        for process_path in sorted_violated_cases:
            sing_pl = "times"
            if process_path[1] == 1:
                sing_pl = "time"
            print("The process path:\n\"{}\" \t was non-conformant {} {}".format(process_path[0], process_path[1],
                                                                                 sing_pl))

        # Output
        print('All in all, {} of {} violated the process model'.format(len(ca.ViolatingTraces),
                                                                       len(event_log.Traces)))
        print('The ratio of violating cases is: {}%'.format(violating_case_ratio))
        print("The conformant traces ratio is: {}%".format(conformance_ratio))
        print("The replay fitness is: {}".format(replay_fitness))
    else:
        print('The conformance ratio is 100%')


def filter_event_log(event_log_path, output_file_name, tau_v, ns=''):
    event_log = Etree.parse(event_log_path)
    root = event_log.getroot()
    all_traces = root.findall(ns + 'trace')
    cnt_fail = len(tau_v)
    cnt = len(all_traces)
    print('# of traces to be filtered: {}'.format(cnt_fail))
    print('# of traces in the event log: {}'.format(cnt))
    for trace in all_traces:
        trace_name = trace.findall(ns + 'string')
        for trace_id in trace_name:
            if trace_id.get('key') == 'concept:name' \
                    and trace_id.get('value') in tau_v:
                root.remove(trace)
    num_filtered = len(root.findall(ns + 'trace'))
    if cnt - cnt_fail == num_filtered:
        print(f"Resulting event log contains {num_filtered} trace(s)")
        print("Event log successfully filtered")
        event_log.write(output_file_name)


def rule_checking(trace, ca):
    """
    The rule checking method gets a trace as an input and then simulates the model with
    the constraints retrieved from the DCR graph.
    :param ca: The conformance analysis data object that is used for the overall conformance checking
    :param trace: the trace that is checked within this thread
    :return:
    """
    marking = Marking.get_initial_marking()
    violated = False
    for event in trace.Events:
        node = dcr_graph.get_node_by_name(event.EventName)
        violated = marking.perform_transition_node(node)
        if violated:
            break
    if not violated and len(marking.PendingResponse) != 0:
        for pending in  marking.PendingResponse:
            if pending in marking.Included:
                violated = True
                break
    if violated:
        ca.append_conformance_data(trace, violated)

def discover(out_file,name):
    log_d = xes_importer.xes.importer.apply(out_file)


    for miner in miners:
        net, im, fm = miners[miner](log_d)
        pviz = vis_factory.visualizer.apply(net, im, fm)
        pviz.render(name)


if __name__ == '__main__':
    main()
