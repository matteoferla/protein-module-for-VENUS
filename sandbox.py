from michelanglo_protein import ProteinAnalyser, ProteinCore, Mutation, structure
from michelanglo_protein.settings_handler import global_settings
from michelanglo_protein.generate import ProteinGatherer, ProteomeGatherer
from michelanglo_protein.generate.split_gnomAD import gnomAD
from michelanglo_protein.protein_analysis import StructureAnalyser
# Settings = namedtuple('settings', 'dictionary_folder', 'reference_folder', 'temp_folder')
import pickle
import sys, traceback, re
from collections import Counter

import pymol2, os

from pprint import PrettyPrinter
pprint = PrettyPrinter().pprint
from multiprocessing import Pool


def test_ProteinAnalyser():
    p = ProteinAnalyser(uniprot = 'Q86V25').load()
    print(p)
    p.mutation = Mutation('p.N127W')
    p.analyse_structure()
    print(p.get_features_near_position())
    print(p.get_gnomAD_near_position())
    print(p.model.get_structure_neighbours())
    print(p.get_superficiality())


# p=ProteinGatherer(uniprot='Q6ZN55').parse_uniprot().parse_pdb_blast()

# from michelanglo_protein.apriori_effect import WikiTable
# print(WikiTable(WikiTable.grantham).ndata)


from michelanglo_protein.generate.uniprot_master_parser import UniprotMasterReader
import os, json
def mini_gene_data():
    genes = '''DOCK180
    DOCK2
    DOCK3
    DOCK4
    DOCK5
    DOCK6
    DOCK7
    DOCK8
    DOCK9
    DOCK10
    DOCK11
    '''.split()


    data = {}
    from pprint import PrettyPrinter
    pprint = PrettyPrinter().pprint
    namedex = json.load(open('data/human_prot_namedex.json'))
    for uni in set(namedex.values()):
        g = ProteinGatherer(uniprot=uni).parse_uniprot()
        data[g.gene_name] = {'name': g.gene_name, 'uniprot': g.uniprot, 'len': len(g), 'domains': {k: g.features[k] for k in ('active site','modified residue','topological domain','domain','region of interest','transmembrane region') if k in g.features}, 'disease': g.diseases}
        #print(g.gene_name,g.uniprot,len(g))
    json.dump(data,open('map.json','w'))

def make_pdb_dex():
    #I need to make a uniprot to pdb dex.
    from michelanglo_protein.generate.uniprot_master_parser import UniprotMasterReader
    master_file = os.path.join(ProteinGatherer.settings.temp_folder, 'uniprot_sprot.xml')
    UniprotMasterReader.make_dictionary(uniprot_master_file=master_file, chosen_attribute='uniprot')

def iterate_taxon(taxid=9606):
    """
    This is an ad hoc fix to fix humans or similar. For full deployment use ProteomeParser.
    :param taxid:
    :return:
    """
    path = os.path.join(global_settings.pickle_folder,f'taxid{taxid}')
    for pf in os.listdir(path):
        try:
            protein = ProteinGatherer().load(file=os.path.join(path, pf))
            protein.gnomAD = []
            protein.parse_gnomAD()
            protein.get_PTM()
            protein.compute_params()
            protein.dump()
            #michelanglo_protein.get_offsets().parse_gnomAD().compute_params()
            #michelanglo_protein.dump()
        except:
            pass

def all_swiss():
    p = Pool(6)
    global_settings.verbose = False
    taxa = (3702, 6239, 7227, 10090, 36329, 83332, 83333, 93061, 190650, 208964, 284812, 559292)  # 9606
    p.map(add_swissmodel, taxa)

def add_swissmodel(taxid=9606):
        print(f'************************ {taxid} *************************************')
        path = os.path.join(global_settings.pickle_folder, f'taxid{taxid}')
        for pf in os.listdir(path):
            p = ProteinGatherer().load(file=os.path.join(path, pf))
            if len(p.sequence) == 0:
                try:
                    global_settings.verbose = True
                    p.parse_uniprot()
                    p.parse_swissmodel()
                    p.compute_params()
                    p.parse_gnomAD()
                    p.get_PTM()
                    assert len(p.sequence) > 0, 'Darn. Sequence is zero AA long'
                    p.dump()
                    global_settings.verbose = False
                except Exception:
                    traceback.print_exc(file=sys.stdout)
            else:
                p.parse_swissmodel()
                p.dump()

def how_many_empty(taxid=9606):
    from collections import Counter
    global_settings.verbose = False
    empty = 0
    full = 0
    path = os.path.join(global_settings.pickle_folder, f'taxid{taxid}')
    for pf in os.listdir(path):
        p = ProteinGatherer().load(file=os.path.join(path, pf))
        if len(p.sequence) == 0:
            print(p)
            empty += 1
        else:
            full +=1
    print(full, empty)

def compress(taxid=9606, target='../gpickle'):
    if not os.path.exists(target):
        os.mkdir(target)
    source = os.path.join(global_settings.pickle_folder, f'taxid{taxid}')
    for pf in os.listdir(source):
        p = ProteinCore().load(file=os.path.join(source, pf))
        p.gdump(file=os.path.join(target, os.path.splitext(pf)[0]+'.gzp'))


def fix_empty(taxid=9606):
    from collections import Counter
    global_settings.verbose = False
    glitchy = 0
    fine = 0
    fixed = 0
    path = os.path.join(global_settings.pickle_folder, f'taxid{taxid}')
    for pf in os.listdir(path):
        p = ProteinGatherer().load(file=os.path.join(path, pf))
        if len(p.sequence) == 0:
            print('****************************************')
            print(f'Attempting to fix {p.gene_name}')
            try:
                global_settings.verbose = True
                p.parse_uniprot()
                p.parse_swissmodel()
                p.compute_params()
                p.parse_gnomAD()
                p.get_PTM()
                assert len(p.sequence) > 0, 'Darn. Sequence is zero AA long'
                p.dump()
                fixed += 1
                global_settings.verbose = False
            except Exception:
                traceback.print_exc(file=sys.stdout)
                glitchy += 1
        else:
            fine +=1
    print('****************************************')
    print(f'Fine: {fine:,}, Fixed {fixed:,}, Glitchy: {glitchy:,}')


def describe(uniprot):
    print('***************** DESCRIPTION *******************************')
    p = ProteinCore(taxid='9606', uniprot=uniprot).load()  # gnb1 P62873 gnb2 P62879
    pprint(p.asdict())

def inspect_offsets(uniprot):
    print('***************** inspect_offsets *******************************')
    p = ProteinCore(taxid='9606', uniprot=uniprot).load()
    for s in p.pdbs:
        print(s.code)
        print(s.chain_definitions)
        print(s._get_sifts())

def fix_offsets(file):
    p = ProteinCore().load(file=file)
    lines = []
    for s in p.pdbs:
        if s.type != 'rcsb':
            continue
        details = s._get_sifts()
        for detail in details:
            ## clean rows
            for k in ('PDB_BEG', 'PDB_END', 'RES_END', 'RES_BEG', 'SP_BEG', 'SP_END'):
                if k == 'None' or k is None:
                    detail[k] = None
                elif isinstance(detail[k], int):
                    pass  # this means so test is being done.
                else:
                    r = re.search('(-?\d+)', detail[k])  # str().isdigit() does not like negatives.
                    if r is None:
                        detail[k] = None
                    else:
                        detail[k] = int(r.group(1))  # yes. py int is signed
            ## get offset
            if detail['PDB_BEG'] is not None:  ##nice.
                offset = detail['SP_BEG'] - detail['PDB_BEG']
            elif detail['PDB_END'] is not None:
                offset = detail['SP_BEG'] - (detail['PDB_END'] - (detail['SP_END'] - detail['SP_BEG']))
            elif detail['SP_BEG']:
                try:
                    offset = s.get_offset_from_PDB(detail, p.sequence)
                except: ## Pymol subclasses BaseException.
                    pass
            else:
                offset = 0
            lines.append(f"{s.code}\t{detail['CHAIN']}\t{detail['SP_PRIMARY']}\t{offset}")
        s.chain_definitions = [{'chain': d['CHAIN'],
                                'uniprot': d['SP_PRIMARY'],
                                'x': d["SP_BEG"],
                                'y': d["SP_END"],
                                'offset': offset,
                                'range': f'{d["SP_BEG"]}-{d["SP_END"]}',
                                'name': None,
                                'description': None} for d in details]
        s.offsets = {d['chain']: d['offset'] for d in s.chain_definitions}
        try:
            if s.chain != '*':
                detail = next(filter(lambda x: s.chain == x['chain'], s.chain_definitions))
                s.offset = detail['offset']
        except:
            pass

    if p.pdbs:
        p.dump()
    return '\n'.join(lines)



def fix_all_offsets():
    p = Pool(6)
    global_settings.verbose = False
    with open('PDB_Uniprot_offsets.tsv', 'w') as w:
        for species in os.listdir(os.path.join(global_settings.pickle_folder)):
            if 'taxid' not in species:
                continue
            if '9606' not in species:
                continue
            source = os.path.join(global_settings.pickle_folder, species)
            blocks = p.map(fix_offsets, [os.path.join(source, pf) for pf in os.listdir(source)])
            w.write('\n'.join(blocks))
            w.write('\n')

def touch_offsets(taxid=9606):
    overview = []
    global_settings.verbose = False
    source = os.path.join(global_settings.pickle_folder, f'taxid{taxid}')
    for pf in os.listdir(source):
        p = ProteinCore().load(file=os.path.join(source, pf))
        for s in p.pdbs:
            if s.type != 'rcsb':
                continue
            details = s._get_sifts()
            v = []
            for detail in details:
                ## clean rows
                for k in ('PDB_BEG', 'PDB_END', 'RES_END', 'RES_BEG', 'SP_BEG', 'SP_END'):
                    if k == 'None' or k is None:
                        detail[k] = None
                    elif isinstance(detail[k], int):
                        pass  # this means so test is being done.
                    else:
                        r = re.search('(-?\d+)', detail[k])  # str().isdigit() does not like negatives.
                        if r is None:
                            detail[k] = None
                        else:
                            detail[k] = int(r.group(1))  # yes. py int is signed
                ## get offset
                if detail['PDB_BEG'] is not None:  ##nice.
                    offset = detail['SP_BEG'] - detail['PDB_BEG']
                    if offset and detail['PDB_BEG'] == detail['RES_BEG']:
                        v.append('off-start')
                    elif offset:
                        v.append('off-unstart')
                    elif detail['SP_BEG'] != 1:
                        v.append('no-off-unstart')
                    else:
                        v.append('no-off-start')
                elif detail['PDB_END'] is not None:
                    offset = detail['SP_BEG'] - (detail['PDB_END'] - (detail['SP_END'] - detail['SP_BEG']))
                    if offset and detail['PDB_END'] == detail['RES_END']:
                        v.append('off-start')
                    elif offset:
                        v.append('off-unstart')
                    elif detail['SP_BEG'] != 1:
                        v.append('no-off-unstart')
                    else:
                        v.append('no-off-start')
                elif detail['SP_BEG'] == 1:
                    offset = 0
                    v.append('no-off-start')
                elif detail['RES_BEG'] == 1:
                    # This is problematic. This means that there are unresolved residues at the N & C termini.
                    # This can go either way.
                    v.append('RES1')
                    offset = 0
                else:
                    v.append('RESn')
                    offset = 0
            if 'RESn' in v or 'RES1' in v:
                offset = s.get_offset_from_PDB(details, p.sequence)
            c = Counter(v).most_common()
            overview.append('+'.join(sorted(set(v))))
    print(Counter(overview).most_common())

def jsonable(self):
    def deobjectify(x):
        if isinstance(x, dict):
            return {k: deobjectify(x[k]) for k in x}
        elif isinstance(x, list) or isinstance(x, set):
            return [deobjectify(v) for v in x]
        elif isinstance(x, int) or isinstance(x, float):
            return x
        else:
            return str(x) # really ought to deal with falseys.
    return {a: deobjectify(getattr(self, a, '')) for a in self.__dict__}

def analyse(uniprot):
    print('***************** ANALYSIS *******************************')
    p = ProteinAnalyser(taxid='9606', uniprot=uniprot).load()
    p.mutation = f'{p.sequence[65]}66W'
    p.predict_effect()
    p.analyse_structure()
    print(p)
    import json
    json.dump(p.asdict(), open('test.json','w'))

    #print('Best one: ',p.get_best_model())
    # print('analysed', {**jsonable(p.structural),
    #     'superficiality': p.structural.get_superficiality(),
    #     'structural_neighbours': list(p.structural.get_structure_neighbours())})
    # http://0.0.0.0:8088/venus_analyse?uniprot=P62879&species=9606&mutation=A73T

def reparse_gene(name):
    human = json.load(open(os.path.join(global_settings.dictionary_folder, 'taxid9606-names2uniprot.json')))
    target = human[name]
    p = ProteinGatherer(uniprot=target)
    p.parse_uniprot()
    print(p.sequence)

if __name__ == '__main__':
    global_settings.verbose = True #False
    global_settings.startup(data_folder='../protein-data')
#### workspace!
if 1==1:
    #os.mkdir(os.path.join(ProteinCore.settings.temp_folder, 'PDB'))
    #describe('P01112')
    #analyse('P62873')
    #how_many_empty()
    #fix_empty()
    #compress()
    #parse_uniprot(
    #inspect_offsets('P01133')
    #touch_offsets()
    #fix_all_offsets()
    all_swiss()
elif 1==9:
    p = ProteinGatherer(taxid='9606', uniprot='P62873').load()
    print(p.gnomAD)
    print(p.parse_gnomAD())
    print(p.gnomAD)
    print(p.features['PSP_modified_residues'])
    from michelanglo_protein.generate.split_phosphosite import Phoshosite
    #ph = Phoshosite().split().write('phosphosite')
    p = ProteinGatherer(taxid='9606', uniprot='P62879').load()
    print(':B and ('+' or '.join([str(m.x) for m in p.gnomAD if m.homozygous])+')')

    print([m for m in p.gnomAD if m.homozygous])
    print(' '.join([str(m.description.split()[0]) for m in p.gnomAD])+')')
    print([m for m in p.gnomAD if m.homozygous])
elif 1==0:
    iterate_taxon('9606')
        #.retrieve_references(ask=False, refresh=False)
    #UniprotMasterReader()

    #global_settings.startup()

    #make_pdb_dex()
    #split_gnomAD.gnomAD().write()
    #iterate_taxon('9606')

    p = ProteinAnalyser(taxid='9606', uniprot='Q9BZ29').load()
    p.mutation = 'P23W'
    print('check_mutation', p.check_mutation())
    print('mutation_discrepancy',p.mutation_discrepancy())
    print('predict_effect', p.predict_effect())
    print('elmdata', p.elmdata)
    print(p.mutation)
    # fetch_binders is too slow. Pre-split the data like for gnomAD.
elif 1==0:
    print('retrieving...')
    global_settings.retrieve_references(ask=False, refresh=False)
else:
    ## dock 9 ops.
    #test_ProteinAnalyser()
    p = ProteinGatherer(uniprot='Q96N67').load()
    p.parse_gnomAD()
    def ncbize(n):
        if n < 1419:
            return n
        elif n < 1832:
            return n+9
        else:
            return n+11
    s = [str(ncbize(v.x)) for v in p.gnomAD]
    for i in range(len(s)//100 + 1):
        print('color yellow, chain A and resi '+'+'.join(s[100*i:100*(i+1)]))
    print('color orange, chain A and resi ' + '+'.join([str(ncbize(v.x)) for v in p.gnomAD if v.impact == 'HIGH']))
    print('color red, chain A and resi '+'+'.join([str(ncbize(v.x)) for v in p.gnomAD if v.homozygous]))
