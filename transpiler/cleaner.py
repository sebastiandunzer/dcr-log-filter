from xml.etree import ElementTree as Etree

def clean_event_log(event_log_path, output_file_name, trace_list, ns=''):
    event_log = Etree.parse(event_log_path)
    root = event_log.getroot()
    all_traces = root.findall(ns + 'trace')
    cnt_fail = len(trace_list)
    cnt = len(all_traces)
    print('# of traces to be filtered: {}'.format(cnt_fail))
    print('# of traces in the event log: {}'.format(cnt))
    for trace in all_traces:
        trace_name = trace.findall(ns + 'string')
        for trace_id in trace_name:
            if trace_id.get('key') == 'concept:name' \
                    and trace_id.get('value') in trace_list:
                root.remove(trace)
                trace_list.remove(trace_id.get('value'))
    num_filtered = len(root.findall(ns + 'trace'))
    if cnt - cnt_fail == num_filtered:
        print("Resulting event log contains {} trace(s)".format(num_filtered))
        print("Event log successfully filtered")
        event_log.write(output_file_name)