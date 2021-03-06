# -*- coding: utf-8 -*-
#BEGIN_HEADER
import os
import json
from Bio import SeqIO
from pprint import pprint, pformat
from AssemblyUtil.AssemblyUtilClient import AssemblyUtil
from KBaseReport.KBaseReportClient import KBaseReport
from DataFileUtil.DataFileUtilClient import DataFileUtil
import subprocess
import os
import re
from pprint import pprint, pformat
from datetime import datetime
import uuid

#END_HEADER


class identify_promoter:
    '''
    Module Name:
    identify_promoter

    Module Description:
    This module has methods for promoter discovery.
get_promoter_for_gene retrieves promoter sequence for a gene
    '''

    ######## WARNING FOR GEVENT USERS ####### noqa
    # Since asynchronous IO can lead to methods - even the same method -
    # interrupting each other, you must be *very* careful when using global
    # state. A method could easily clobber the state set by another while
    # the latter method is running.
    ######################################### noqa
    VERSION = "0.0.1"
    GIT_URL = "https://github.com/arwyer/identify_promoter.git"
    GIT_COMMIT_HASH = "421f8f35d1f7e225b22dded28f8005fbcb0afd8a"

    #BEGIN_CLASS_HEADER

    #END_CLASS_HEADER

    # config contains contents of config file in a hash or None if it couldn't
    # be found
    def __init__(self, config):
        #BEGIN_CONSTRUCTOR
        self.callback_url = os.environ['SDK_CALLBACK_URL']
        self.shared_folder = config['scratch']
        #END_CONSTRUCTOR
        pass

    def get_promoter_for_gene(self, ctx, params):
        """
        :param params: instance of type "get_promoter_for_gene_input" (Genome
           is a KBase genome Featureset is a KBase featureset Promoter_length
           is the length of promoter requested for all genes) -> structure:
           parameter "genome_ref" of String, parameter "featureSet_ref" of
           String, parameter "promoter_length" of Long
        :returns: instance of type "get_promoter_for_gene_output_params" ->
           structure: parameter "report_name" of String, parameter
           "report_ref" of String
        """
        # ctx is the context object
        # return variables are: output
        #BEGIN get_promoter_for_gene
        #code goes here
        dfu = DataFileUtil(self.callback_url)
        objectRefs = {'object_refs':[params['Genome'],params['featureSet']]}
        objects = dfu.get_objects(objectRefs)
        genome = objects['data'][0]['data']
        featureSet = objects['data'][1]['data']
        assembly_ref = {'ref': genome['assembly_ref']}
        with open('/kb/module/work/genome.json','w') as f:
            json.dump(genome,f)
        with open('/kb/module/work/featureSet.json','w') as f:
            json.dump(featureSet,f)
        #with open('/kb/module/work/asssembly.json','w') as f:
        #    json.dump(assembly,f)
        print('Downloading Assembly data as a Fasta file.')
        assemblyUtil = AssemblyUtil(self.callback_url)
        fasta_file = assemblyUtil.get_assembly_as_fasta(assembly_ref)

        #pprint(fasta_file)
        #loop over featureSet
        #find matching feature in genome
        #get record, start, orientation, length
        #TODO: add some error checking logic to the bounds of the promoter
        prom= ""
        for feature in featureSet['elements']:
            #print(feature)
            #print(featureSet['elements'][feature])
            for f in genome['features']:
                if f['id'] == feature:
                    attributes = f['location'][0]
                    #print(f['location'])
                    break
            for record in SeqIO.parse(fasta_file['path'], 'fasta'):
                #print(record.id)
                #print(attributes[0])
                if record.id == attributes[0]:
                    #print(attributes[0])
                    if attributes[2] == '+':
                        #might need to offset by 1?
                        end = attributes[1]
                        start = end - params['promoter_length']
                        if end < 0:
                            end = 0
                        promoter = record.seq[start:end].upper()
                        prom += ">" + feature + "\n"
                        prom += promoter + "\n"


                    elif attributes[2] == '-':
                        start = attributes[1]
                        end = start + params['promoter_length']
                        if end > len(record.seq) - 1:
                            end = len(record.seq) - 1
                        promoter = record.seq[start:end].upper()
                        complement = {'A': 'T', 'C': 'G', 'G': 'C', 'T': 'A'}
                        promoter = ''.join([complement[base] for base in promoter[::-1]])
                        prom += ">" + feature + "\n"
                        prom += promoter + "\n"


                    else:
                        print('Error on orientation')


        timestamp = int((datetime.utcnow() - datetime.utcfromtimestamp(0)).total_seconds()*1000)
        html_output_dir = os.path.join(self.shared_folder,'output_html.'+str(timestamp))
        if not os.path.exists(html_output_dir):
            os.makedirs(html_output_dir)
        html_file = 'promoter.html'
        output_html_file_path = os.path.join(html_output_dir, html_file);


        html_report_lines = "<html><body>"
        html_report_lines += "<pre>" + prom + "</pre>" 
        html_report_lines += "</body></html>"

        with open (output_html_file_path, 'w', 0) as html_handle:
            html_handle.write(html_report_lines)

        try:
            html_upload_ret = dfu.file_to_shock({'file_path': html_output_dir,
            #html_upload_ret = dfu.file_to_shock({'file_path': output_html_file_path,
                                                 #'make_handle': 0})
                                                 'make_handle': 0,
                                                 'pack': 'zip'})
        except:
            raise ValueError ('error uploading HTML file to shock')

        reportName = 'identify_promoter_report_'+str(uuid.uuid4())

        reportObj = {'objects_created': [],
                     'message': '',  
                     'direct_html': None,
                     'direct_html_index': 0,
                     'file_links': [],
                     'html_links': [],
                     'html_window_height': 220,
                     'workspace_name': params['workspace_name'],
                     'report_object_name': reportName
                     }


        # attach to report obj
        #reportObj['direct_html'] = None
        reportObj['direct_html'] = ''
        reportObj['direct_html_link_index'] = 0
        reportObj['html_links'] = [{'shock_id': html_upload_ret['shock_id'],
                                    'name': html_file,
                                    'label': 'View'
                                    }
                                   ]

        report = KBaseReport(self.callback_url, token=ctx['token'])
        #report_info = report.create({'report':reportObj, 'workspace_name':input_params['input_ws']})
        report_info = report.create_extended_report(reportObj)
        output = { 'report_name': report_info['name'], 'report_ref': report_info['ref'] }



        #iterate over records in fasta
        #for record in SeqIO.parse(fasta_file['path'], 'fasta'):


        #objects list of Genome and featureSet

        #pprint(objects)
        #END get_promoter_for_gene

        # At some point might do deeper type checking...
        if not isinstance(output, dict):
            raise ValueError('Method get_promoter_for_gene return value ' +
                             'output is not type dict as required.')
        # return the results
        return [output]
    def status(self, ctx):
        #BEGIN_STATUS
        returnVal = {'state': "OK",
                     'message': "",
                     'version': self.VERSION,
                     'git_url': self.GIT_URL,
                     'git_commit_hash': self.GIT_COMMIT_HASH}
        #END_STATUS
        return [returnVal]
