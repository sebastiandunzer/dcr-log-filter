# coding=utf-8
"""The main file of the dcr-cc that is executed"""
from threading import Thread

import os.path
import pickle

import cmd_parser
import eventlog_parser
from result_data import RuleViolation, RuleViolationTrace
from graph import DCRGraph
from marking import Marking
from xml.etree import ElementTree as Etree
from pm4py.algo.conformance.tokenreplay import algorithm as token_replay
from pm4py.conformance import precision_token_based_replay
from pm4py.objects.petri_net import importer
import pm4py.convert

from sklearn.metrics import classification_report

from pandas import DataFrame

import pm4py.discovery as discovery
import pm4py.objects.log.importer as xes_importer



miners = {
    'inductive': discovery.discover_petri_net_inductive,
    'alpha': discovery.discover_petri_net_alpha,
    'alpha_plus': discovery.discover_petri_net_alpha_plus,
    'heuristics': discovery.discover_petri_net_heuristics,
    'ilp': discovery.discover_petri_net_ilp

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
    model_import_path = args.importModel
    miner_name = args.minerName
    import_successful = False

    name = xml_path.split('/')[-1].split('.')[0]
    name_tau_v = name + "_tauv.txt"
    name_tau_c = name + "_tauc.txt"
    path_tau_v = f"Resources/pickle/{name_tau_v}"
    path_tau_c = f"Resources/pickle/{name_tau_c}"

    if os.path.exists(path_tau_v) and  os.path.exists(path_tau_c):
        with open(path_tau_v, "rb") as f:
            tau_v = pickle.load(f)
        with open(path_tau_c, "rb") as f:
            tau_c = pickle.load(f)
        import_successful = True

    if not import_successful:
        tau_v, tau_c = perform_rule_checking(data_path, xml_path)
        with open(path_tau_v, "wb") as f:
            pickle.dump(tau_v, f)
        with open(path_tau_c, "wb") as f:
            pickle.dump(tau_c, f)
        import_successful = True

    if not os.path.exists(out_path):
        clean_event_log(data_path, out_path, tau_v, ns)

    if model_import_path:
        net, im, fm = importer.importer.apply(model_import_path)
        verify_imported_model(data_path, tau_v, tau_c, name, net, im, fm, miner_name)
    else:
        verify(data_path, tau_v, tau_c, out_path, name)




def perform_rule_checking(data_path, xml_path):
    global dcr_graph
    dcr_graph = DCRGraph.get_graph_instance(xml_path)
    event_log = eventlog_parser.get_event_log(data_path)
    ca = RuleViolation()
    # throughput
    # if parallel is set: a thread pool is created
    threads = []
    for trace in event_log.Traces:
        t = Thread(target=rule_checking, args=(trace, ca))
        threads.append(t)
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    create_conformance_output(ca, event_log)
    tau_v = [trace.TraceId for trace in ca.ViolatingTraces]
    tau_c = [trace.TraceId for trace in event_log.Traces]
    tau_c = list(set(tau_c) - set(tau_v))
    return tau_v, tau_c


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

        # Sort the dictionaries for the descending order of occurrences
        sorted_including_violation = sorted(ca.ViolatedActivities.items(), key=lambda kv: kv[1], reverse=True)
        sorted_violated_roles = sorted(ca.ViolatedRoles.items(), key=lambda kv: kv[1], reverse=True)
        sorted_violated_pending = sorted(ca.ViolatedPending.items(), key=lambda kv: kv[1], reverse=True)
        sorted_violated_connections = sorted(ca.ViolatedConnections.items(), key=lambda kv: kv[1], reverse=True)
        sorted_violated_cases = sorted(ca.create_violated_traces_dict().items(), key=lambda kv: kv[1], reverse=True)

        # Print all detailed information
        print("\n{} process paths failed the events\n".format(len(sorted_violated_cases)))
        for process_path in sorted_violated_cases:
            sing_pl = "times"
            if process_path[1] == 1:
                sing_pl = "time"
            print("The process path:\n\"{}\" \t was non-conformant {} {}".format(process_path[0], process_path[1],
                                                                                 sing_pl))
        for included_violation in sorted_including_violation:
            print('The activity \"{}\" has been executed {} times even though it was not included'.format(
                included_violation[0], included_violation[1]))
        for violated_role in sorted_violated_roles:
            print('The role \"{}\" was misused \"{}\" times'.format(violated_role[0], violated_role[1]))
        for violated_pending in sorted_violated_pending:
            print('The activity {} was pending at the end in {} cases'.format(violated_pending[0], violated_pending[1]))
        for violated_connection in sorted_violated_connections:
            print('The {} was violated in {} traces'.format(violated_connection[0], violated_connection[1]))

        # Output
        print('All in all, {} of {} violated the process model'.format(len(ca.ViolatingTraces),
                                                                       len(event_log.Traces)))
        print('The ratio of violating cases is: {}%'.format(violating_case_ratio))
        print("The conformant traces ratio is: {}%".format(conformance_ratio))
        print("The replay fitness is: {}".format(replay_fitness))
    else:
        print('The conformance ratio is 100%')


def clean_event_log(event_log_path, output_file_name, tau_v, ns=''):
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
    trace_conformance_data = RuleViolationTrace(trace)
    for event in trace.Events:
        node = dcr_graph.get_node_by_name(event.EventName)
        marking.perform_transition_node(node, event, trace_conformance_data)
    if len(marking.PendingResponse) != 0:
        for pending in marking.PendingResponse:
            if pending in marking.Included:
                trace_conformance_data.add_violating_pending(pending.ActivityName)
    if trace_conformance_data.HasViolations:
        ca.append_conformance_data(trace_conformance_data)


def verify_imported_model(log_file, tau_v, tau_c, name, net, im, fm, miner_name):
    log = xes_importer.xes.importer.apply(log_file)
    all_traces = sorted(tau_v + tau_c)
    data_all_traces = convert_to_data_traces(all_traces, set(tau_v))

    correct_traces, failed_traces = run_token_replay(net, im, fm, log)

    all_traces_p = sorted(correct_traces + failed_traces)
    data_all_traces_p = convert_to_data_traces(all_traces_p, set(failed_traces))

    output_dict = classification_report(data_all_traces, data_all_traces_p, output_dict=True)
    DataFrame(output_dict).to_csv(f"Results/results_{name}_{miner_name}.csv")

    if failed_traces == tau_v:
        print('Equivalent')
    else:
        print("Not Equivalent")
        print(f"Detected {len(failed_traces)} failed traces instead of {len(tau_v)}")


def verify(log_file, tau_v, tau_c, out_file, name):
    log = xes_importer.xes.importer.apply(log_file)
    log_d = xes_importer.xes.importer.apply(out_file)

    all_traces = sorted(tau_v + tau_c)
    data_all_traces = convert_to_data_traces(all_traces, set(tau_v))

    for miner in miners:

        net, im, fm = miners[miner](log_d)
        # pviz = vis_factory.visualizer.apply(net, im, fm)
        # pviz.view()

        correct_traces, failed_traces = run_token_replay(net, im, fm, log)

        all_traces_p = sorted(correct_traces + failed_traces)
        data_all_traces_p = convert_to_data_traces(all_traces_p, set(failed_traces))

        output_dict = classification_report(data_all_traces, data_all_traces_p, output_dict=True)
        DataFrame(output_dict).to_csv(f"Results/results_{name}_{miner}.csv")

        if failed_traces == tau_v:
            print('Equivalent')
        else:
            print("Not Equivalent")
            print(f"Detected {len(failed_traces)} failed traces instead of {len(tau_v)}")


def run_token_replay(net, im, fm, log):
    index = 0
    failed_traces = []
    correct_traces = []
    replay_results = token_replay.apply(log, net, im, fm)
    for result in replay_results:
        if not result.get('trace_is_fit'):
            failed_traces.append(log[index].attributes["concept:name"])
        else:
            correct_traces.append(log[index].attributes["concept:name"])
        index += 1
    return correct_traces, failed_traces


def convert_to_data_traces(all_traces, lookup_space):
    data_traces = all_traces
    for i in range(len(all_traces)):
        if data_traces[i] in lookup_space:
            data_traces[i] = 0
        else:
            data_traces[i] = 1
    return data_traces


if __name__ == '__main__':
    main()
