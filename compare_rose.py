#!/usr/bin/python3.6
#compare_rose_jobs
#compares two rose suites
# v0.1
# Dan Hodson
# 29/Jul/2025

import os
import difflib
import argparse
import configparser

def read_file_lines(path):
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        return f.readlines()


def configparser_read_with_header(configFilePath):
    with open(configFilePath) as stream:
        header=''
        config_string=stream.read()
        #don#t attempt to substitue when you encounter %value%
        #don't worry if there are sections with identical section names
        config=configparser.ConfigParser(interpolation=None,strict=False)
        #loop over config string removing the first line at each pass
        #if the first line does not start with a bracket, it must be a header line, not a config line
        #store this in the header string and move on
        #if it DOES contain a [ it must be a config line, so patch back together, read the config and
        #pass the head and config back
        while True:

            tmp,config_string=config_string.split('\n',1)
            if '[' in tmp:
                config.read_string(tmp+'\n'+config_string)
                break
            else:
                header+=tmp
        return(config,header)


def compare_ini_files(file1, file2):
    #config1 = configparser.ConfigParser()
    #config2 = configparser.ConfigParser()

    #config1.read(file1)
    #config2.read(file2)
    global suite1,suite2

    config1,header1=configparser_read_with_header(file1)
    config2,header2=configparser_read_with_header(file2)


    # Compare sections                                                                                                     
    sections1 = set(config1.sections())
    sections2 = set(config2.sections())

    diff_result = []
    # Sections in file1 but not in file2

    cylc_flag=False
    #we want to allow differences in section heading for cylc8 and cylc7
    if 'meta.conf' in file1:
        tmp=set()
        for section in sections1:
            if 'jinja2:suite.rc' in section:
                cylc_flag=True
                section=section.replace('jinja2:suite.rc','template variables')
            tmp.add(section)
        sections1=tmp
                
        tmp=set()
        for section in sections2:
            if 'jinja2:suite.rc' in section:
                cylc_flag=True
                section=section.replace('jinja2:suite.rc','template variables')
            tmp.add(section)
        sections2=tmp

    if cylc_flag:
        log_print(">> DIFFERENT CYLC versions - allowing equivalent sections names")
    
    for section in sections1 - sections2:
        diff_result.append(f"Section [{section}] only in {file1}\n")

    # Sections in file2 but not in file1                                                                                  
    for section in sections2 - sections1:
        diff_result.append(f"Section [{section}] only in {file2}\n")

    sections1 = set(config1.sections())
    sections2 = set(config2.sections())
    
        
    # Compare options in common sections                                                                                  
    for section in sections1 & sections2:
        options1 = set(config1[section])
        options2 = set(config2[section])

        # Options in file1 but not in file2                                                                               
        for option in options1 - options2:
            diff_result.append(f"Option {option} in section [{section}] only in {file1}\n")

        # Options in file2 but not in file1                                                                               
        for option in options2 - options1:
            diff_result.append(f"Option {option} in section [{section}] only in {file2}\n")

        # Compare values of common options                                                                                
        for option in options1 & options2:
            if config1[section][option] != config2[section][option]:
                diff_result.append(f"  [{section}]{option}: \n\t{suite1} {config1[section][option]}\n\t{suite2} {config2[section][option]}\n")

    return diff_result

def compare_files(file1, file2):                                                                                          
    if file1.endswith('.conf') and file2.endswith('.conf'):
        return compare_ini_files(file1, file2)                                                                            
    else:                                                                                                                 
        lines1 = read_file_lines(file1)                                                                                   
        lines2 = read_file_lines(file2)                                                                                   
        diff = list(difflib.unified_diff(                                                                                 
            lines1, lines2,                                                                                               
            fromfile=file1, tofile=file2,                                                                                 
            lineterm=''                                                                                                   
        ))                                                                                                                
    return diff                                                                                                            

def list_files(root):
    file_list = []
    for dirpath, dirnames, filenames in os.walk(root):
        # Exclude hidden directories
        dirnames[:] = [d for d in dirnames if not d.startswith('.')]
        for filename in filenames:
            rel_path = os.path.relpath(os.path.join(dirpath, filename), root)
            file_list.append(rel_path)
    return sorted(file_list)


def get_suite(job):
    #if job does not contain the suite name, expand the path and try again!
    if not 'u-' in job:
        job=os.path.abspath(job)
    if not 'u-' in job:
        log_print(f'unknown suite in {job}')
    suite=job.split('/')[-1] 
    return(suite)

def get_log_filename(suite1, suite2):
    """Generate log filename based on the two suites being compared"""
    return f"comparison_{suite1}_{suite2}.log"

def log_print(message, log_file=None):
    """Print to console and log file"""
    print(message)
    if log_file:
        print(message, file=log_file)

def compare_jobs(job1, job2):
    global suite1, suite2
    
    suite1 = get_suite(job1)
    suite2 = get_suite(job2)
    
    # Open log file
    log_filename = get_log_filename(suite1, suite2)
    with open(log_filename, 'w') as log_file:
        
        files1 = list_files(job1)
        files2 = list_files(job2)

        set1 = set(files1)
        set2 = set(files2)

        only_in_1 = sorted(set1 - set2)
        only_in_2 = sorted(set2 - set1)
        in_both = sorted(set1 & set2)

        log_print("=== Comparison Summary ===", log_file)
        if only_in_1:
            log_print(f"\nFiles only in {job1}:", log_file)
            for f in only_in_1:
                log_print(f"  - {f}", log_file)
        if only_in_2:
            log_print(f"\nFiles only in {job2}:", log_file)
            for f in only_in_2:
                log_print(f"  - {f}", log_file)

        log_print("\n=== Differences in Common Files ===", log_file)
        for f in in_both:
            path1 = os.path.join(job1, f)
            path2 = os.path.join(job2, f)
            diff = compare_files(path1, path2)
            if diff:
                log_print(f"\n--- Difference in file: {f} ---", log_file)
                for line in diff:
                    log_print(line, end='', log_file)
                log_print("", log_file)  # spacing

# def compare_jobs(job1, job2):
#     global suite1,suite2
    
#     suite1=get_suite(job1)
#     suite2=get_suite(job2)


    
#     files1 = list_files(job1)
#     files2 = list_files(job2)

#     set1 = set(files1)
#     set2 = set(files2)

#     only_in_1 = sorted(set1 - set2)
#     only_in_2 = sorted(set2 - set1)
#     in_both = sorted(set1 & set2)

#     print("=== Comparison Summary ===")
#     if only_in_1:
#         print(f"\nFiles only in {job1}:")
#         for f in only_in_1:
#             print(f"  - {f}")
#     if only_in_2:
#         print(f"\nFiles only in {job2}:")
#         for f in only_in_2:
#             print(f"  - {f}")

#     print("\n=== Differences in Common Files ===")
#     for f in in_both:
#         path1 = os.path.join(job1, f)
#         path2 = os.path.join(job2, f)
#         diff = compare_files(path1, path2)
#         if diff:
#             print(f"\n--- Difference in file: {f} ---")
#             for line in diff:
#                 print(line, end='')
#             print()  # spacing



            
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compare two Rose/Cylc jobs.")
    parser.add_argument("job1", help="Path to first job directory")
    parser.add_argument("job2", help="Path to second job directory")
    args = parser.parse_args()

    if not os.path.isdir(args.job1) or not os.path.isdir(args.job2):
        print("Both arguments must be valid directories.")
    else:
        compare_jobs(args.job1, args.job2)
