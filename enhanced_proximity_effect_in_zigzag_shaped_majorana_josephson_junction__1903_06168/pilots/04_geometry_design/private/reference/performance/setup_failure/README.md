# Preserved harness setup failure, not numerical evidence

The initial controller set both its soft and hard address-space limit to 1 GiB. Child workers could not raise their inherited hard limit to the intended 2 GiB; they failed before entering the forward model. This is a harness defect, not a physical-kernel or optimization failure, and is excluded from the acceptance comparison.

The corrected controller keeps a 1 GiB soft limit and a 6 GiB hard ceiling so children may establish their own 2 GiB hard limit. The direct search is restarted with a fresh full 1200-second budget. Already completed dense probes were performed before the faulty parent limit and remain valid; they are not repeated. Initial setup artifacts are preserved here for audit.
