from typing import Optional

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from tqdm import tqdm

from scheduler import BaseScheduler


class DiffusionModule(nn.Module):
    def __init__(self, network, var_scheduler: BaseScheduler, **kwargs):
        super().__init__()
        self.network = network
        self.var_scheduler = var_scheduler

    def get_loss(self, x0, class_label=None, noise=None):
        ######## TODO ########
        # DO NOT change the code outside this part.
        # compute noise matching loss.
        # x0 is of shape [B, C, 3], C is 96
        assert x0.dtype == torch.float32
        B = x0.shape[0]
        timestep = self.var_scheduler.uniform_sample_t(B, self.device)
        pen_state = x0[:, :, 2:]
        
        noise_pred, pen_state_pred = self.network(x0[:, :, :2], timestep, class_label)
        if noise is None:
            noise = torch.randn_like(noise_pred, device=self.device)

        noise_criterion = nn.MSELoss()
        pen_state_criterion = nn.CrossEntropyLoss()

        loss = noise_criterion(noise_pred, noise) + 0.01 * pen_state_criterion(pen_state_pred, pen_state)
        ######################
        return loss
    
    @property
    def device(self):
        return next(self.network.parameters()).device

    @property
    def Nmax(self):
        return self.network.Nmax

    @torch.no_grad()
    def sample(
        self,
        batch_size,
        return_traj=False,
        class_label: Optional[torch.Tensor] = None,
        guidance_scale: Optional[float] = 0.0,
    ):
        x_T = torch.randn([batch_size, self.Nmax, 2], device=self.device, dtype=torch.float32)
        do_classifier_free_guidance = guidance_scale > 0.0

        if do_classifier_free_guidance:

            ######## TODO ########
            # Assignment 2-3. Implement the classifier-free guidance.
            # Specifically, given a tensor of shape (batch_size,) containing class labels,
            # create a tensor of shape (2*batch_size,) where the first half is filled with zeros (i.e., null condition).
            
            assert class_label is not None
            assert len(class_label) == batch_size, f"len(class_label) != batch_size. {len(class_label)} != {batch_size}"
            raise NotImplementedError("TODO")
            #######################

        traj = [x_T]
        pen_state_traj = []
        for t in self.var_scheduler.timesteps:
            x_t = traj[-1]
            if do_classifier_free_guidance:
                ######## TODO ########
                # Assignment 2. Implement the classifier-free guidance.
                raise NotImplementedError("TODO")
                #######################
            else:
                noise_pred, pen_state_pred = self.network(
                    x_t,
                    timestep=t.to(self.device),
                    class_label=class_label,
                )
                # print(f"샘플링 timestep {t}에서 noise_pred", torch.isnan(noise_pred).any())
                # print(f"샘플링 timestep {t}에서 pen_state_pred", torch.isnan(pen_state_pred).any())

            x_t_prev = self.var_scheduler.step(x_t, t, noise_pred)
            
            traj[-1] = traj[-1].cpu()
            traj.append(x_t_prev.detach())
            pen_state_traj.append(pen_state_pred.detach())

        if return_traj:
            return traj, pen_state_traj
        else:
            return traj[-1], pen_state_traj[-1]

    def save(self, file_path):
        hparams = {
            "network": self.network,
            "var_scheduler": self.var_scheduler,
            } 
        state_dict = self.state_dict()

        dic = {"hparams": hparams, "state_dict": state_dict}
        torch.save(dic, file_path)

    def load(self, file_path):
        dic = torch.load(file_path, map_location="cpu")
        hparams = dic["hparams"]
        state_dict = dic["state_dict"]

        self.network = hparams["network"]
        self.var_scheduler = hparams["var_scheduler"]

        self.load_state_dict(state_dict)