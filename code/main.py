import os
import sys
import glob
import subprocess


def copy_results(base_dir, results_dir):
    # tar up all json results in base dir
    result_tar = os.path.join(results_dir, f"{os.path.basename(base_dir)}.tar")
    result_jsons = glob.glob(os.path.join(base_dir, "*", "*", "run", "*", "*results*json"))
    print(f"copying {result_jsons} results to {result_tar}..")

    subprocess.run([
        "tar", 
        "-cvf",
        result_tar,
        *result_jsons
    ])

    # extract to results_dir to keep directory structure
    subprocess.run([
        "tar",
        "-xvf",
        result_tar,
        "-C",
        os.path.dirname(result_tar)
    ])


def run_all_from_base_dir(base_dir):
    # get base_dir
    base_dir = os.path.abspath(base_dir)
    print(f"base dir: {base_dir}")

    # get all rounds (sparsities)
    rounds = [
        x for x in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, x))
    ]
    print(f"{base_dir} rounds: ", rounds)

    for rnd in rounds:
        # get all setups (networks)
        round_dir = os.path.join(base_dir, rnd)
        setups = [
            x
            for x in os.listdir(round_dir)
            if os.path.isdir(os.path.join(round_dir, x)) and '.zarr' not in x
        ]
        print(f"{round_dir} setups: ", setups)

        for setup in setups:
            # get dirs
            run_dir = os.path.join(base_dir, rnd, setup, "run")

            # train
            train_config = os.path.join(run_dir, "01_train.toml")
            subprocess.run(["bs", "train", train_config])

            # predict
            pred_dirs = [
                x
                for x in os.listdir(run_dir)
                if os.path.isdir(os.path.join(run_dir, x))
            ]
            print(f"{run_dir} preds: ", pred_dirs)
            
            for pred_dir in pred_dirs:
                prefix = os.path.join(run_dir, pred_dir)
                print(prefix)
                subprocess.run(["bs", "pred", os.path.join(prefix, "02_pred_volume_2.toml")])

                # segment mutex watershed
                for bias in [f"[{short},{short},{short},{long},{long},{long}]" for short in [-0.35, -0.4, -0.5] for long in [-0.75, -0.8, -0.9]]:
                    for sigma in [
                            "[0,1,1]",
                            "None",
                            ]:
                        subprocess.run(
                            [
                                "bs",
                                "seg",
                                os.path.join(prefix, "03_mws_volume_2.toml"),
                                "-p",
                                f"bias={bias}",
                                "-p",
                                f"sigma={sigma}"
                            ]
                        )

                # segment watershed
                for merge_function in ["mean", "hist_quant_75"]:
                    for sigma in [
                            "[0,1,1]",
                            "None",
                            ]:
                        subprocess.run(
                            [
                                "bs", 
                                "seg", 
                                os.path.join(prefix, "03_ws_volume_2.toml"),
                                "-p",
                                f"merge_function={merge_function}",
                                "-p",
                                f"sigma={sigma}"
                            ]
                        )

                # eval
                subprocess.run(
                    ["bs", "eval", os.path.join(prefix, "04_eval_volume_2.toml")]
                )


if __name__ == "__main__":
    # make variations
    subprocess.run(["python", "make_variations.py"])

    # get all base directories
    all_base_dirs = [x for x in os.listdir() if os.path.isdir(x)]
    print(all_base_dirs)

    # run all
    for base_dir in all_base_dirs:
        run_all_from_base_dir(base_dir)
        # copy results to /results
        result_dir = os.path.dirname(os.path.abspath(base_dir))
        result_dir = os.path.join(os.path.dirname(result_dir), 'results')
        copy_results(base_dir, result_dir)
        print("done!")
