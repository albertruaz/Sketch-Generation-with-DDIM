import argparse

import numpy as np
import torch
from dataset import pen_state_to_binary, tensor_to_pil_image
from model import DiffusionModule
from scheduler import DDPMScheduler
from pathlib import Path


def main(args):
    save_dir = Path(args.save_dir)
    save_dir.mkdir(exist_ok=True, parents=True)

    device = f"cuda:{args.gpu}"

    ddpm = DiffusionModule(None, None)
    ddpm.load(args.ckpt_path)
    ddpm.eval()
    ddpm = ddpm.to(device)

    num_train_timesteps = ddpm.var_scheduler.num_train_timesteps
    ddpm.var_scheduler = DDPMScheduler(
        num_train_timesteps,
        beta_1=1e-4,
        beta_T=0.02,
        mode="linear",
    ).to(device)

    total_num_samples = 20
    num_batches = int(np.ceil(total_num_samples / args.batch_size))

    for i in range(num_batches):
        sidx = i * args.batch_size
        eidx = min(sidx + args.batch_size, total_num_samples)
        B = eidx - sidx

        if args.use_cfg:  # Enable CFG sampling
            assert ddpm.network.use_cfg, f"The model was not trained to support CFG."
            vectors, pen_states = ddpm.sample(
                B,
                class_label=torch.randint(1, 4, (B,)),
                guidance_scale=args.cfg_scale,
            )
        else:
            vectors, pen_states = ddpm.sample(
                B,
                class_label=torch.randint(1, 4, (B,)),
                guidance_scale=0.0,
            )

        samples = torch.cat((vectors, pen_states), dim=-1)
        samples = pen_state_to_binary(samples)
        pil_images = [tensor_to_pil_image(sample) for sample in samples]

        for j, img in zip(range(sidx, eidx), pil_images):
            img.save(save_dir / f"{j}.png")
            print(f"Saved the {j}-th image.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch_size", type=int, default=4)
    parser.add_argument("--gpu", type=int, default=0)
    parser.add_argument("--ckpt_path", type=str, default='results/diffusion-ddpm-11-18-120918/step=12000_ema.ckpt')
    parser.add_argument("--save_dir", type=str, default='samples/')
    parser.add_argument("--use_cfg", action="store_true")
    parser.add_argument("--sample_method", type=str, default="ddpm")
    parser.add_argument("--cfg_scale", type=float, default=7.5)

    args = parser.parse_args()
    main(args)
