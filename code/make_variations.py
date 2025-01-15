import glob
import os
import shutil
import bootstrapper
import toml


def replace_all(text, replacements):
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text

def recursively_modify(path, func):
    for root, _, files in os.walk(path):
        for file in files:
            if file.endswith(".toml"):
                with open(os.path.join(root, file), "r") as f:
                    content = f.read()
                modified_content = func(content)
                with open(os.path.join(root, file), "w") as f:
                    f.write(modified_content)

def make_recursive_copy(src, dst):
    shutil.copytree(src, dst)

if __name__ == "__main__":
    # modify below to include desired variations
    datasets = {
        # name: voxel_size
        "cremi_a": [40, 8, 8,],
        "cremi_b": [40, 8, 8,],
        "cremi_c": [40, 8, 8,],
        "epi": [235, 75, 75],
        "fib25": [8, 8, 8],
        "voljo": [50, 8, 8]        
    }
    reps = ["rep_1", "rep_2", "rep_3"]
    sparsities = ["dense", "sparse_2d", "sparse_3d"]

    pred_iters_2d = [10000, 20000]
    pred_iters_2dto3d = [5000, 10000]

    # path of this file
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # starter example
    starter = "example"
    example_sparsity_dir = os.path.join(starter, "SPARSITY")
    example_run_dir = os.path.join(example_sparsity_dir, "2d_mtlsd_3ch", "run")

    # make pred variations for starter
    for iter1 in pred_iters_2d:
        for iter2 in pred_iters_2dto3d:
            example_pred_run_dir = os.path.join(example_run_dir, f"ITER2_3Af2M--ITER1")
            pred_run_dir = os.path.join(example_run_dir, f"{iter2}_3Af2M--{iter1}")
            replacements = {
                "ITER1": str(iter1),
                "ITER2": str(iter2),
                "BS_PATH": bootstrapper.__path__[0],
                "BASE": base_path
            }
            make_recursive_copy(example_pred_run_dir, pred_run_dir)
            recursively_modify(example_run_dir, lambda x: replace_all(x, replacements))
    shutil.rmtree(example_pred_run_dir)

    # make sparsity variations for starter
    for sparsity in sparsities:
        sparsity_dir = example_sparsity_dir.replace("SPARSITY", sparsity)
        make_recursive_copy(example_sparsity_dir, sparsity_dir)
        recursively_modify(sparsity_dir, lambda x: replace_all(x, {"SPARSITY": sparsity}))
    shutil.rmtree(example_sparsity_dir)

    # make dataset and rep variations
    for ds in datasets:
        for rep in reps:
            base_dir = f"{ds}_{rep}"
            make_recursive_copy(starter, base_dir)
            recursively_modify(base_dir, lambda x: replace_all(x, {"DATASET": ds, "REP": rep}))
        
        # recursive glob for train.toml files
        train_tomls = glob.glob(f"{ds}*/*/*/*/01_train.toml")
        print(train_tomls)
        for train_toml in train_tomls:
            with open(train_toml, "r") as f:
                toml_data = toml.load(f)

            # modify voxel size
            voxel_size = datasets[ds]
            toml_data["voxel_size"] = voxel_size

            # add mask for voljo
            if ds == "voljo":
                toml_data["samples"][0]["mask"] = toml_data["samples"][0]["raw"] + "_mask"

            with open(train_toml, "w") as f:
                toml.dump(toml_data, f)

        # recursive glob for seg tomls
        seg_tomls = glob.glob(f"{ds}*/*/*/*/*/03*toml")
        for seg_toml in seg_tomls:
            if ds == "voljo":
                with open(seg_toml, "r") as f:
                    toml_data = toml.load(f)
                if "volume_2" in seg_toml:
                    toml_data["mask_dataset"] = os.path.join(base_path, "data", ds, "volume_2.zarr", "raw_mask")
                elif "volume_1" in seg_toml:
                    toml_data["mask_dataset"] = os.path.join(base_path, "data", ds, "volume_1.zarr", "raw_mask")
                with open(seg_toml, "w") as f:
                    toml.dump(toml_data, f)
    shutil.rmtree(starter)