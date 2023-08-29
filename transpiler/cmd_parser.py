# coding=utf-8
"""Contains methods for command line interaction"""
import argparse

# {http://www.xes-standard.org/}

def parse_args():
    """
    Creates the argument parser for the command line
    :return: the args that were parsed from the command line
    """
    # This file contains the commandline tools for the current tool
    parser = argparse.ArgumentParser(prog='main.py', usage='main.py [options]')
    parser.add_argument('--eventLog', nargs='?', default='Resources/Hospital_Billing.xes',
                        help='The path pulling the event log')
    parser.add_argument('--XmlDcr', nargs="?", default='Resources/Hospital_Billing.xml',
                        help='The input path for the DCR Graph xml')
    parser.add_argument('--output', nargs='?')
    parser.add_argument('--namespace', nargs='?', default='')
    parser.add_argument('--outFile', nargs='?', default="Resources/Hospital_Billing_prep.xes")
    parser.add_argument('--importModel', nargs='?', default="Resources/Hospital_Billing_Filtered.pnml")
    parser.add_argument('--minerName',nargs='?', default="trace")

    return parser.parse_args()
