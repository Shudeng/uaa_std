import os
from db import Model as DB
from east import Model as east
from textbox import Model as textbox
from craft_ import Model as craft
from eval_helper import Eval
from icdar_dataset import ICDARDataset
from totaltext_dataset import TotalText
from attack_util import generate_universal_examples
import json
import torch

tmp_file = os.path.join(os.getcwd(), "tmp_transferdataset.txt")

def get_model(model_name, dataset_name):
    if model_name=="db": return DB(dataset_name)
    if model_name=="east": return east()
    if model_name=="textbox": return textbox()
    if model_name=="craft": return craft(dataset_name)

def get_dataset(dataset_name):
    if 'icdar' in dataset_name:
        return ICDARDataset()
    else:
        return TotalText()

def get_latex(res_dict):
    target_models = [
            [model_name, dataset_name] 
            for dataset_name in ['icdar2015', 'total_text']
            for model_name in ['craft', 'db']
            ]
    latex_str = ""

    for source_model_name in ['craft', 'db']:
        latex_str += "\multirow{6}{*}[-4pt]{\\thead{" + source_model_name.upper() + "}}\n"


        for dataset_name in ['icdar2015', 'total_text']:
            if 'icdar' in dataset_name:
                latex_str += "& ICDAR &-&-&-&-&-&-\\\\\n" 
            else:
                latex_str += "& TotalText &-&-&-&-&-&-\\\\\n" 

            for pert_dataset_name in ['icdar2015', 'total_text']:
                latex_str += "& {}+{} &".format(
                        "ICDAR+" if 'icdar' in dataset_name else 'TotalText',
                        "P_i" if 'icdar' in pert_dataset_name else "P_t")
                metrics = []
            
                for target_model in ['craft', 'db']:
                    key = f"{target_model}: {dataset_name},{dataset_name}, /data/attacks/res_{source_model_name}/universal/momentumFalse_diFalse_tiFalse_featureFalse_eps13{'' if 'icdar' in pert_dataset_name else 'total_text'}/perturbation.pt, /data/attacks/"
                    #key = f"{target_model}: {dataset_name},{dataset_name}, /data/attacks/res_{source_model_name}/universal/momentumFalse_diTrue_tiTrue_featureTrue_eps13{'' if 'icdar' in pert_dataset_name else 'total_text'}/perturbation.pt, /data/attacks/"
                    if key in res_dict:
                        val = res_dict[key]

                        metrics += [val['precision']]
                        metrics += [val['recall']]
                        metrics += [val['hmean']]
                    else:
                        metrics += [10,10,10]

                metrics = [str(int(item*1000)/1000) if item!=10 else '-' for item in metrics]
                latex_str += "&".join(metrics)+"\\\\\n"
        latex_str += "\\midrule\n"

    print(latex_str)


def parse_tmp(tmp_file=tmp_file):
    if not os.path.exists(tmp_file): return {}
    with open(tmp_file, "r") as infile:
        lines = [item.strip() for item in infile.readlines()]
    def line2key(line):
        line=line.replace("_", "")
        line=line.replace("Precision", "")
        line=line.replace("/Recall", "")
        line=line.replace("hmean", "")
        items = line.split(":")
        return {
                'precision': float(items[1][:5]),
                'recall': float(items[2][:5]),
                'hmean': float(items[3][:5])
                }



    res = {}
    for line in lines:
        if 'Precision:_' in line:
            key = line2key(line)
            continue
        out = line.split('tmp_imgs,')

        if not "None" in out[1]:
            res[out[0]] = json.loads(out[1].split("!")[-1])
        else:
            res[out[0]] = key
        
    return res





def eval_transferdataset(
        model_dataset_name,
        dataset_name,
        model_name,
        eval_helper, 
        img_dir=os.path.join(os.getcwd(), "tmp_imgs")):

    os.system("rm -rf {}".format(img_dir))
    eval_helper=Eval(dataset_name)

    model = get_model(model_name, model_dataset_name)
    dataset = get_dataset(dataset_name)
    perturbation = torch.load(perturbation_path)
    #model.generate_universal_examples(dataset, perturbation, img_dir)
    generate_universal_examples(model, dataset, perturbation, img_dir)
    res=eval_helper.eval(model, img_dir, res_dir=os.path.join(os.getcwd(), "tmp_txt")+"/")
                    
    with open(tmp_file, "a") as f: f.write("{}: {},{}, {}, {}, {}\n".format(model_name,model_dataset_name, dataset_name, perturbation_path, img_dir, res))


if __name__=="__main__":
    perturbation_paths = []
    for model_name in ['db', 'craft']:
        for dataset_name in ['icdar2015', 'total_text']:
            if dataset_name=='total_text' and model_name in ['textbox', 'east']: continue
            perturbation_paths += [
                    os.path.join(
                        os.getcwd(),
                        "res_{}/universal/momentumFalse_diFalse_tiFalse_featureFalse_eps13{}/perturbation.pt".format(
                        #"res_{}/universal/momentumFalse_diTrue_tiTrue_featureTrue_eps13{}/perturbation.pt".format(
                            model_name,
                            "" if "icdar" in dataset_name else "total_text"
                            )
                        )
                    ]

    res_dict = parse_tmp()
    get_latex(res_dict)
    import pdb; pdb.set_trace()
    img_dir = os.path.join(os.getcwd(), "tmp_imgs")

    for model_name in ['db', 'craft']:
        for model_dataset_name in ['total_text', 'icdar2015']:
            for dataset_name in ['total_text', 'icdar2015']:
                if model_dataset_name=='total_text' and model_name in ['textbox', 'east']: continue
                for perturbation_path in perturbation_paths:
                    if not os.path.exists(perturbation_path):
                        print(perturbation_path)
                        continue
                    #import pdb; pdb.set_trace()
                    if "{}: {},{}, {}, {}, {}\n".format(model_name,model_dataset_name,dataset_name, perturbation_path, img_dir, "").split("tmp_imgs,")[0] in res_dict: continue
                    eval_transferdataset(model_dataset_name, dataset_name, model_name, perturbation_path, img_dir)
        

