'''
Functions that are used while a Generation is being Evaluated 
'''
import os
import random
import multiprocessing
from rdkit import Chem
import numpy as np
from random import randrange
import discriminator as D
import evolution_functions as evo
from SAS_calculator.sascorer import calculateScore
manager = multiprocessing.Manager()
lock = multiprocessing.Lock()

#Added to deal with Similarity:                                         #!# ----------------------------------------
from rdkit.Chem import AllChem
from rdkit.Chem.rdMolDescriptors import GetUSRScore, GetUSRCAT

def calc_prop_USR(unseen_smile_ls, property_name, props_collect):
    '''Calculate Similarity for each molecule in unseen_smile_ls, and record results
       in locked dictionary props_collect 
    '''

    #To provide reference molecule:
    reference_smile = 'C1(=NC(=NC2=C1N=C[N]2[H])N(C3=CC=C(C=C3)[S](=O)(=O)N([H])[H])[H])C4=CC(=CC=C4)C5=CC=CC=C5'
    ref_mol = Chem.MolFromSmiles(reference_smile)
    AllChem.EmbedMolecule(ref_mol, useRandomCoords = True, enforceChirality = False)
    ref_embed_usrcat = GetUSRCAT(ref_mol)
    
    for smile in unseen_smile_ls:
        mol, smi_canon, did_convert = evo.sanitize_smiles(smile) #esure valid smile
        if did_convert:
            try:
                mol_test = Chem.MolFromSmiles(smile)
                mol_test = Chem.AddHs(mol_test)
                AllChem.EmbedMolecule(mol_test, useRandomCoords = True, enforceChirality = False)
                mol_test = Chem.RemoveHs(mol_test)
                UsrcatMol = GetUSRCAT(mol_test)
            except ValueError: 
                SimScore = 0
            else:
                SimScore = GetUSRScore(ref_embed_usrcat, UsrcatMol)
            props_collect[property_name][smile] = SimScore
        else:
            raise Exception('Invalid smile encountered while atempting to calculate Similarity') #!# ----------------

#Added to deal with Tanimoto
from rdkit import DataStructs

def calc_prop_Tanimoto(unseen_smile_ls, property_name, props_collect):                  #-------------------------
    '''Calculate Tanimoto Coeff. for each molecule in unseen_smile_ls, and record results
       in locked dictionary props_collect 
    '''

    #To provide reference molecule:
    reference_smile = 'C1(=NC(=NC2=C1N=C[N]2[H])N(C3=CC=C(C=C3)[S](=O)(=O)N([H])[H])[H])C4=CC(=CC=C4)C5=CC=CC=C5'
    Tani_ref_mol = Chem.MolFromSmiles(reference_smile)
    Tani_ref_FP = Chem.RDKFingerprint(Tani_ref_mol)

    for smile in unseen_smile_ls:
        mol, smi_canon, did_convert = evo.sanitize_smiles(smile) #esure valid smile
        if did_convert:
            mol_Tani_test = Chem.MolFromSmiles(smile)
            Tani_mol_FP = Chem.RDKFingerprint(mol_Tani_test)
            TaniScore = DataStructs.FingerprintSimilarity(Tani_mol_FP, Tani_ref_FP)
            props_collect[property_name][smile] = TaniScore
        else:
            raise Exception('Invalid smile encountered while atempting to calculate Tanimoto') #----------------

def calc_prop_logP(unseen_smile_ls, property_name, props_collect):
    '''Calculate logP for each molecule in unseen_smile_ls, and record results
       in locked dictionary props_collect 
    '''
    for smile in unseen_smile_ls:
        mol, smi_canon, did_convert = evo.sanitize_smiles(smile)
        if did_convert:                                          # ensure valid smile 
            props_collect[property_name][smile] = evo.get_logP(mol) # Add calculation
        else:
            raise Exception('Invalid smile encountered while atempting to calculate logP')

        
def calc_prop_SAS(unseen_smile_ls, property_name, props_collect):
    '''Calculate synthetic accesibility score for each molecule in unseen_smile_ls,
       results are recorded in locked dictionary props_collect 
    '''
    for smile in unseen_smile_ls:
        mol, smi_canon, did_convert = evo.sanitize_smiles(smile)
        if did_convert:                                         # ensure valid smile 
            props_collect[property_name][smile] = calculateScore(mol)
        else:
            raise Exception('Invalid smile encountered while atempting to calculate SAS ', smile)

    

def calc_prop_RingP(unseen_smile_ls, property_name, props_collect):
    '''Calculate Ring penalty for each molecule in unseen_smile_ls,
       results are recorded in locked dictionary props_collect 
    '''
    for smi in unseen_smile_ls:
        mol, smi_canon, did_convert = evo.sanitize_smiles(smi)
        if did_convert:    
            cycle_list = mol.GetRingInfo().AtomRings() 
            if len(cycle_list) == 0:
                cycle_length = 0
            else:
                cycle_length = max([ len(j) for j in cycle_list ])
            if cycle_length <= 6:
                cycle_length = 0
            else:
                cycle_length = cycle_length - 6
            props_collect[property_name][smi] = cycle_length
        else:
            raise Exception('Invalid smile encountered while atempting to calculate Ring penalty ', smi)
            
            
def calc_prop_SIMIL(starting_smile, unseen_smile_ls, property_name, props_collect):
    '''Calculate logP for each molecule in unseen_smile_ls, and record results
       in locked dictionary props_collect 
    '''
    target, _, _ = evo.sanitize_smiles(starting_smile)

    for smile in unseen_smile_ls:
        mol, smi_canon, did_convert = evo.sanitize_smiles(smile)
        if did_convert:                                                                # ensure valid smile 
            props_collect[property_name][smile] = evo.molecule_similarity(mol, target) # Add calculation
        else:
            raise Exception('Invalid smile encountered while atempting to calculate SIMILARITY: ', smile)


def create_parr_process(chunks, property_name, starting_smile):
    ''' Create parallel processes for calculation of properties
    '''
    # Assign data to each process 
    process_collector    = []
    collect_dictionaries = []
        
    for item in chunks:
        props_collect  = manager.dict(lock=True)
        smiles_map_    = manager.dict(lock=True)
        props_collect[property_name] = smiles_map_
        collect_dictionaries.append(props_collect)
        
        if property_name == 'logP':
            process_collector.append(multiprocessing.Process(target=calc_prop_logP, args=(item, property_name, props_collect, )))
        
        if property_name == 'SAS': 
           process_collector.append(multiprocessing.Process(target=calc_prop_SAS, args=(item, property_name, props_collect, )))
            
        if property_name == 'RingP': 
            process_collector.append(multiprocessing.Process(target=calc_prop_RingP, args=(item, property_name, props_collect, )))
            
        if property_name == 'SIMILR': 
            process_collector.append(multiprocessing.Process(target=calc_prop_SIMIL, args=(starting_smile, item, property_name, props_collect, )))

        if property_name == 'USRSim':               #!# 
            process_collector.append(multiprocessing.Process(target=calc_prop_USR, args=(item, property_name, props_collect, )))

        if property_name == 'TaniSim':               #!# 
            process_collector.append(multiprocessing.Process(target=calc_prop_Tanimoto, args=(item, property_name, props_collect, )))
    
    
    for item in process_collector:
        item.start()
    
    for item in process_collector: # wait for all parallel processes to finish
        item.join()   
        
    combined_dict = {}             # collect results from multiple processess
    for i,item in enumerate(collect_dictionaries):
        combined_dict.update(item[property_name])

    return combined_dict


def fitness(molecules_here,    properties_calc_ls,  
            discriminator,     disc_enc_type,   generation_index,
            max_molecules_len, device,          num_processors,    writer, beta, data_dir, starting_smile, desired_delta, save_curve):
    ''' Calculate fitness fo a generation in the GA
    
    All properties are standardized based on the mean & stddev of the zinc dataset
    
    Parameters:
    molecules_here    (list)         : List of a string of molecules
    properties_calc_ls               : List of propertoes to calculate
    discriminator     (torch.Model)  : Pytorch classifier 
    disc_enc_type     (string)       : Indicated type of encoding shown to discriminator
    generation_index  (int)          : Which generation indicator
    max_molecules_len (int)          : Largest mol length
    device            (string)       : Device of discrimnator  
        
    Returns:
    fitness                   (np.array) : A lin comb of properties and 
                                           discriminator predictions
    discriminator_predictions (np.array) : The predictions made by the discrimantor
    
    '''    
    if properties_calc_ls == None:
        raise Exception('Fail discrm trying to be invoked')
        fitness = discriminator_predictions
    
    else:
        
        molecules_here_unique = list(set(molecules_here))      
        
        
        ratio            = len(molecules_here_unique) / num_processors 
        chunks           = evo.get_chunks(molecules_here_unique, num_processors, ratio) 
        chunks           = [item for item in chunks if len(item) >= 1]
        # Parallelize the calculation of logPs
        if 'logP' in properties_calc_ls:
            logP_results = create_parr_process(chunks, 'logP', starting_smile)

        # Parallelize the calculation of SAS
        if 'SAS' in properties_calc_ls:
            SAS_results = create_parr_process(chunks, 'SAS', starting_smile)

        # Parallize the calculation of Ring Penalty
        if 'RingP' in properties_calc_ls:
            ringP_results = create_parr_process(chunks, 'RingP', starting_smile)

        # Parallelize the calculation of SIMILR    
        if 'SIMILR' in properties_calc_ls:
            similar_results = create_parr_process(chunks, 'SIMILR', starting_smile)

        # Parallize the calculation of USRCAT Sim                               #!#
        if 'USRSim' in properties_calc_ls:
            USRSim_results = create_parr_process(chunks, 'USRSim', starting_smile)

        # Parallize the calculation of Tanimoto                                 #!#
        if 'TaniSim' in properties_calc_ls:
            TaniSim_results = create_parr_process(chunks, 'TaniSim', starting_smile)

        
        logP_calculated, SAS_calculated, RingP_calculated, logP_norm, SAS_norm, RingP_norm, Similarity_calculated, USRSim_calculated, USRSim_norm, TaniSim_calculated, TaniSim_norm = obtained_standardized_properties(molecules_here, logP_results, SAS_results, ringP_results, similar_results, USRSim_results, TaniSim_results)
        
        # Add objective
        fitness = (USRSim_norm)
        
        
        # Similarity Based Fitness _________
        writer.add_scalar('Mean Similarty',        Similarity_calculated.mean(), generation_index) # Mean similarity
        writer.add_scalar('Max  Similarty',        max(Similarity_calculated),   generation_index) # Max similarity
        
        Similarity_calculated = np.array([0 if x > desired_delta else -10**6 for x in Similarity_calculated])
        Similarity_calculated = Similarity_calculated.reshape((fitness.shape[0], 1))

        fitness = fitness + Similarity_calculated
        
        
        # Plot fitness without discriminator 
        writer.add_scalar('max fitness without discr',  max(fitness),     generation_index)
        save_curve.append(max(fitness))
        writer.add_scalar('avg fitness without discr',  fitness.mean(),   generation_index)
        
        # max fitness without discriminator
        f = open('{}/max_fitness_no_discr.txt'.format(data_dir), 'a+')
        f.write(str(max(fitness)[0]) + '\n')
        f.close()
        # avg fitness without discriminator
        f = open('{}/avg_fitness_no_discr.txt'.format(data_dir), 'a+')
        f.write(str(fitness.mean()) + '\n')
        f.close()
        
        
#        fitness = (beta * discriminator_predictions) + fitness
        
        # Plot fitness with discriminator 
        writer.add_scalar('max fitness with discrm',  max(fitness),     generation_index)   
        writer.add_scalar('avg fitness with discrm',  fitness.mean(),   generation_index)   

        # max fitness with discriminator
        f = open('{}/max_fitness_discr.txt'.format(data_dir), 'a+')
        f.write(str(max(fitness)[0]) + '\n')
        f.close()
        # avg fitness with discriminator
        f = open('{}/avg_fitness_discr.txt'.format(data_dir), 'a+')
        f.write(str(fitness.mean()) + '\n')
        f.close()
        
        
        # Plot properties 
        writer.add_scalar('non standr max logp',   max(logP_calculated),         generation_index) # logP plots      
        writer.add_scalar('non standr mean logp',  logP_calculated.mean(),       generation_index)                    
        writer.add_scalar('non standr min sas',    min(SAS_calculated),          generation_index) # SAS plots  
        writer.add_scalar('non standr mean sas',   SAS_calculated.mean(),        generation_index)
        writer.add_scalar('non standr min ringp',  min(RingP_calculated),        generation_index) # RingP plots
        writer.add_scalar('non standr mean ringp', RingP_calculated.mean(),      generation_index)
        writer.add_scalar('non standr max USRCAT Similarity', max(USRSim_calculated), generation_index) # USRCAT Similarity plots             #!#
        writer.add_scalar('non standr mean USRCAT Similarity', USRSim_calculated.mean(), generation_index)
        writer.add_scalar('non standr max Tanimoto Similarity', max(TaniSim_calculated), generation_index) # Tanimoto Similarity plots        #!#
        writer.add_scalar('non standr mean Tanimoto Similarity', TaniSim_calculated.mean(), generation_index)


        # max logP - non standardized
        f = open('{}/max_logp.txt'.format(data_dir), 'a+')
        f.write(str(max(logP_calculated)) + '\n')
        f.close()
        # mean logP - non standardized
        f = open('{}/avg_logp.txt'.format(data_dir), 'a+')
        f.write(str(logP_calculated.mean()) + '\n')
        f.close()
        # min SAS - non standardized 
        f = open('{}/min_SAS.txt'.format(data_dir), 'a+')
        f.write(str(min(SAS_calculated)) + '\n')
        f.close()
        # mean SAS - non standardized 
        f = open('{}/avg_SAS.txt'.format(data_dir), 'a+')
        f.write(str(SAS_calculated.mean()) + '\n')
        f.close()
        # min RingP - non standardized 
        f = open('{}/min_RingP.txt'.format(data_dir), 'a+')
        f.write(str(min(RingP_calculated)) + '\n')
        f.close()
        # mean RingP - non standardized 
        f = open('{}/avg_RingP.txt'.format(data_dir), 'a+')
        f.write(str(RingP_calculated.mean()) + '\n')
        f.close()        
        # max USRCAT Similarity - non standardised                             #!#
        f = open('{}/max_Similarity.txt'.format(data_dir), 'a+')
        f.write(str(max(USRSim_calculated)) + '\n')
        f.close()
        # mean USRCAT Similarity - non standardized                            #!#
        f = open('{}/avg_Similarity.txt'.format(data_dir), 'a+')
        f.write(str(USRSim_calculated.mean()) + '\n')
        f.close()
        # max Tanimoto Similarity - non standardised                           #!#
        f = open('{}/max_Tanimoto.txt'.format(data_dir), 'a+')
        f.write(str(max(TaniSim_calculated)) + '\n')
        f.close()
        # mean Tanimoto Similarity - non standardized                          #!#
        f = open('{}/avg_Tanimoto.txt'.format(data_dir), 'a+')
        f.write(str(TaniSim_calculated.mean()) + '\n')
        f.close()
        
    return fitness, logP_calculated, SAS_calculated, RingP_calculated, USRSim_calculated, TaniSim_calculated 


def obtained_standardized_properties(molecules_here,  logP_results, SAS_results, ringP_results, similar_results, USRSim_results, TaniSim_results):     #!#
    ''' Obtain calculated properties of molecules in molecules_here, and standardize
    values base on properties of the Zinc Data set. 
    '''
    logP_calculated       = []
    SAS_calculated        = []
    RingP_calculated      = []
    Similarity_calculated = []
    USRSim_calculated     = [] #!#
    TaniSim_calculated    = [] #!#

    for smi in molecules_here:
        logP_calculated.append(logP_results[smi])
        SAS_calculated.append(SAS_results[smi])
        RingP_calculated.append(ringP_results[smi])
        Similarity_calculated.append(similar_results[smi])
        USRSim_calculated.append(USRSim_results[smi])               #!#
        TaniSim_calculated.append(TaniSim_results[smi])             #!#
    logP_calculated  = np.array(logP_calculated)
    SAS_calculated   = np.array(SAS_calculated)
    RingP_calculated = np.array(RingP_calculated)
    Similarity_calculated = np.array(Similarity_calculated)
    USRSim_calculated = np.array(USRSim_calculated)         #!#
    TaniSim_calculated = np.array(TaniSim_calculated)       #!#

    
    # Standardize logP based on zinc logP (mean: 2.4729421499641497 & std : 1.4157879815362406)
    logP_norm = (logP_calculated - 2.4729421499641497) / 1.4157879815362406
    logP_norm = logP_norm.reshape((logP_calculated.shape[0], 1))  
    
    # Standardize SAS based on zinc SAS(mean: 3.0470797085649894    & std: 0.830643172314514)
    SAS_norm = (SAS_calculated - 3.0470797085649894) / 0.830643172314514
    SAS_norm = SAS_norm.reshape((SAS_calculated.shape[0], 1))  
    
    # Standardiize RingP based on zinc RingP(mean: 0.038131530820234766 & std: 0.2240274735210179)
    RingP_norm = (RingP_calculated - 0.038131530820234766) / 0.2240274735210179
    RingP_norm = RingP_norm.reshape((RingP_calculated.shape[0], 1))

    # Standardize USRCAT Similarity based on zinc ChemBL Similarity(mean: 3.053230897406870 & std: 0.834794987448313)                #!#     
    USRSim_norm = (USRSim_calculated - 0.186428542) / 0.035664915
    USRSim_norm = USRSim_norm.reshape((USRSim_calculated.shape[0], 1))                                                               #!#
    
    # Standardize Tanimoto Similarity based on ChemBL Tanimoto Similarity(mean: 0.350252265668509 & std: 0.0681108949632873)         #!#     
    TaniSim_norm = (TaniSim_calculated - 0.350252265668509) / 0.0681108949632873
    TaniSim_norm = TaniSim_norm.reshape((TaniSim_calculated.shape[0], 1))                                                            #!#
    
    return logP_calculated, SAS_calculated, RingP_calculated, logP_norm, SAS_norm, RingP_norm, Similarity_calculated, USRSim_calculated, USRSim_norm, TaniSim_calculated, TaniSim_norm
        

def obtain_fitness(disc_enc_type, smiles_here, selfies_here, properties_calc_ls, 
                   discriminator, generation_index, max_molecules_len, device, generation_size, num_processors, writer, beta, image_dir, data_dir, starting_smile, desired_delta, save_curve):
    ''' Obtain fitness of generation based on choices of disc_enc_type.
        Essentially just calls 'fitness'
    '''
    # ANALYSE THE GENERATION                        #!#
    if disc_enc_type == 'smiles' or disc_enc_type == 'properties_rdkit':
        fitness_here, logP_calculated, SAS_calculated, RingP_calculated, USRSim_calculated, TaniSim_calculated = fitness(smiles_here,   properties_calc_ls ,   discriminator, 
                                                                           disc_enc_type, generation_index,   max_molecules_len, device, num_processors, writer, beta, data_dir, starting_smile, desired_delta, save_curve) 
    elif disc_enc_type == 'selfies':
        fitness_here, logP_calculated, SAS_calculated, RingP_calculated, USRSim_calculated, TaniSim_calculated = fitness(selfies_here,  properties_calc_ls ,   discriminator, 
                                                                           disc_enc_type, generation_index,   max_molecules_len, device, num_processors, writer, beta, data_dir, starting_smile, desired_delta, save_curve) 
        


    fitness_here = fitness_here.reshape((generation_size, ))
    order, fitness_ordered, smiles_ordered, selfies_ordered = order_based_on_fitness(fitness_here, smiles_here, selfies_here)    

    # Order molecules based on ordering of 'smiles_ordered'
    logP_calculated  = [logP_calculated[idx] for idx in order]
    SAS_calculated   = [SAS_calculated[idx] for idx in order]
    RingP_calculated = [RingP_calculated[idx] for idx in order]
    USRSim_calculated = [USRSim_calculated[idx] for idx in order]                       #!#
    TaniSim_calculated = [TaniSim_calculated[idx] for idx in order]                     #!#
    
    os.makedirs('{}/{}'.format(data_dir, generation_index))
    #  Write ordered smiles in a text file
    f = open('{}/{}/smiles_ordered.txt'.format(data_dir, generation_index), 'a+')
    f.writelines(["%s\n" % item  for item in smiles_ordered])
    f.close()
    #  Write logP of ordered smiles in a text file
    f = open('{}/{}/logP_ordered.txt'.format(data_dir, generation_index), 'a+')
    f.writelines(["%s\n" % item  for item in logP_calculated])
    f.close()
    #  Write sas of ordered smiles in a text file
    f = open('{}/{}/sas_ordered.txt'.format(data_dir, generation_index), 'a+')
    f.writelines(["%s\n" % item  for item in SAS_calculated])
    f.close()
    #  Write ringP of ordered smiles in a text file
    f = open('{}/{}/ringP_ordered.txt'.format(data_dir, generation_index), 'a+')
    f.writelines(["%s\n" % item  for item in RingP_calculated])
    f.close()
    #  Write USRCAT Similarity of ordered smiles in a text file                                        #!#
    f = open('{}/{}/USRCATSimilarity_ordered.txt'.format(data_dir, generation_index), 'a+')
    f.writelines(["%s\n" % item  for item in USRSim_calculated])
    f.close()
    #  Write Tanimoto Similarity of ordered smiles in a text file                                      #!#
    f = open('{}/{}/Tanimoto_ordered.txt'.format(data_dir, generation_index), 'a+')
    f.writelines(["%s\n" % item  for item in TaniSim_calculated])
    f.close()


    #print statement for the best molecule in the generation
    print('Best best molecule in generation ', generation_index)
    print('    smile  : ', smiles_ordered[0])
    print('    fitness: ', fitness_ordered[0])
    print('    logP   : ', logP_calculated[0])
    print('    sas    : ', SAS_calculated[0])
    print('    ringP  : ', RingP_calculated[0])
    print('    USRCAT : ', USRSim_calculated[0])                               #!#
    print('    Tanimoto : ', TaniSim_calculated[0])                            #!#                                                                                      #!#  --> Another Similarity change to the right and two lines down |
                                                                                                                                                                        #!#                                                                V 
    
    f = open('{}/best_in_generations.txt'.format(data_dir), 'a+')
    best_gen_str = 'index: {},  smile: {}, fitness: {}, logP: {}, sas: {}, ringP: {}, USRCAT: {}, Tanimoto: {}'.format(generation_index, smiles_ordered[0], fitness_ordered[0], logP_calculated[0], SAS_calculated[0], RingP_calculated[0], USRSim_calculated[0], TaniSim_calculated[0])
    f.write(best_gen_str + '\n')
    f.close()
                                                                                                            #!# -->
    show_generation_image(generation_index, image_dir, smiles_ordered, fitness_ordered, logP_calculated, SAS_calculated, RingP_calculated, USRSim_calculated, TaniSim_calculated)    
        
    return fitness_here, order, fitness_ordered, smiles_ordered, selfies_ordered


def show_generation_image(generation_index, image_dir, smiles_ordered, fitness, logP, SAS, RingCount, USRSim, TaniSim):  #!#
    ''' Plot 100 molecules with the best fitness in in a generation 
        Called after at the end of each generation. Image in each generation
        is stored with name 'generation_index.png'
    
    Images are stored in diretory './images'
    '''
    if generation_index > 1:
        A = list(smiles_ordered) 
        A = A[:100]
        if len(A) < 100 : return #raise Exception('Not enough molecules provided for plotting ', len(A))
        A = [Chem.MolFromSmiles(x) for x in A]
        
        evo.create_100_mol_image(A, "./{}/{}_ga.png".format(image_dir, generation_index), fitness, logP, SAS, RingCount, USRSim, TaniSim)    #!#


def obtain_previous_gen_mol(starting_smiles,  starting_selfies, generation_size,
                            generation_index, selfies_all,      smiles_all):
    '''Obtain molecules from one generation prior.
       If generation_index is 1, only the the starting molecules are returned 
       
     Parameters:
         
     Returns: 
    
    '''
    # Obtain molecules from the previous generation 
    
    if generation_index == 1:
        
        
        randomized_smiles  = []
        randomized_selfies = []
        for i in range(generation_size): # nothing to obtain from previous gen
                                         # So, choose random moleclues from the starting list 
            index = randrange(len(starting_smiles))
            randomized_smiles.append(starting_smiles[index])
            randomized_selfies.append(starting_selfies[index])

        return randomized_smiles, randomized_selfies
    else:
        return smiles_all[generation_index-2], selfies_all[generation_index-2]
    


def order_based_on_fitness(fitness_here, smiles_here, selfies_here):
    '''Order elements of a lists (args) based om Decreasing fitness 
    '''
    order = np.argsort(fitness_here)[::-1] # Decreasing order of indices, based on fitness 
    fitness_ordered = [fitness_here[idx] for idx in order]
    smiles_ordered = [smiles_here[idx] for idx in order]
    selfies_ordered = [selfies_here[idx] for idx in order]
    
    return order, fitness_ordered, smiles_ordered, selfies_ordered


def apply_generation_cutoff(order, generation_size):
    ''' Return of a list of indices of molecules that are kept (high fitness)
        and a list of indices of molecules that are replaced   (low fitness)
        
    The cut-off is imposed using a Fermi-Function
        
    Parameters:
    order (list)          : list of molecule indices arranged in Decreasing order of fitness
    generation_size (int) : number of molecules in a generation
    
    Returns:
    to_replace (list): indices of molecules that will be replaced by random mutations of 
                       molecules in list 'to_keep'
    to_keep    (list): indices of molecules that will be kept for the following generations
    '''
    # Get the probabilities that a molecule with a given fitness will be replaced
    # a fermi function is used to smoothen the transition
    positions     = np.array(range(0, len(order))) - 0.2*float(len(order))
    probabilities = 1.0 / (1.0 + np.exp(-0.02 * generation_size * positions / float(len(order))))        
    
    to_replace = [] # all molecules that are replaced 
    to_keep    = [] # all molecules that are kept 
    for idx in range(0,len(order)):
        if np.random.rand(1) < probabilities[idx]:
            to_replace.append(idx)
        else:
            to_keep.append(idx)

    return to_replace, to_keep

    
def obtain_next_gen_molecules(order,           to_replace,     to_keep, 
                              selfies_ordered, smiles_ordered, max_molecules_len):
    ''' Obtain the next generation of molecules. Bad molecules are replaced by 
    mutations of good molecules 
    
    Parameters:
    order (list)            : list of molecule indices arranged in Decreasing order of fitness
    to_replace (list)       : list of indices of molecules to be replaced by random mutations of better molecules
    to_keep (list)          : list of indices of molecules to be kept in following generation
    selfies_ordered (list)  : list of SELFIE molecules, ordered by fitness 
    smiles_ordered (list)   : list of SMILE molecules, ordered by fitness 
    max_molecules_len (int) : length of largest molecule 
    
    Returns:
    smiles_mutated (list): next generation of mutated molecules as SMILES
    selfies_mutated(list): next generation of mutated molecules as SELFIES
    '''
    smiles_mutated = []
    selfies_mutated = []
    for idx in range(0,len(order)):
        if idx in to_replace: # smiles to replace (by better molecules)
            random_index=np.random.choice(to_keep, size=1, replace=True, p=None)[0]                             # select a random molecule that survived
            grin_new, smiles_new = evo.mutations_random_grin(selfies_ordered[random_index], max_molecules_len)  # do the mutation

            # add mutated molecule to the population
            smiles_mutated.append(smiles_new)
            selfies_mutated.append(grin_new)
        else: # smiles to keep
            smiles_mutated.append(smiles_ordered[idx])
            selfies_mutated.append(selfies_ordered[idx])
        
    return smiles_mutated, selfies_mutated
   
    

def update_gen_res(smiles_all, smiles_mutated, selfies_all, selfies_mutated, smiles_all_counter):
    '''Collect results that will be shared with global variables outside generations
    '''
    smiles_all.append(smiles_mutated)
    selfies_all.append(selfies_mutated)
    
    for smi in smiles_mutated:
        if smi in smiles_all_counter:
            smiles_all_counter[smi] += 1
        else:
            smiles_all_counter[smi] = 1
    
    return smiles_all, selfies_all, smiles_all_counter



        
        


    
    
