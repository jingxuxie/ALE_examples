# -*- coding: utf-8 -*-
# Copyright 2016-2019 tkwant authors.
#
# This file is part of tkwant.  It is subject to the license terms in the file
# LICENSE.rst found in the top-level directory of this distribution and at
# http://kwant-project.org/license.  A list of tkwant authors can be found in
# the file AUTHORS.rst at the top-level directory of this distribution and at
# http://kwant-project.org/authors.
"""Tools parallelizing tkwant with the Message Passing Interface (MPI)."""

import numpy as np
from . import _logging

__all__ = ['communicator_init', 'communicator_free', 'get_communicator',
           'distribute_dict', 'DistributedDict', 'round_robin', 'get_rank']


def get_rank():
    """Return the mpi rank of tkwants global communicator as a dict value"""
    rank = get_communicator().rank
    return {'rank': rank}


# set module logger
logger = _logging.make_logger(name=__name__)


_COMM = None  # the global MPI communicator used by tkwant by default.

# it is prefered to use ``get_communicator`` to use the
# global tkwant communicator as this will properly initialize it
# if required. alternatively one may use ``communicator_init``
# if a custom MPI communicator should be used for tkwant.


def communicator_init(comm=None):
    """Initialize a global MPI communicator for tkwant.

    Parameters
    ----------
    comm : `mpi4py.MPI.Intracomm`, optional
        MPI communicator that tkwant will use.
        By default, this routine initializes the communicator to MPI.COMM_WORLD.
        Note that this routine will always initialize the global
        communicator with a dublicate.
    """
    global _COMM
    if _COMM is None:
        if comm is None:
            from mpi4py import MPI
            _COMM = MPI.COMM_WORLD.Dup()
        else:
            _COMM = comm.Dup()
    else:
        logger.warning("tkwant MPI communicator cannot be reinitialized.")


def communicator_free():
    """Free the global tkwant MPI communicator"""
    global _COMM
    _COMM.Free()


def get_communicator(comm=None):
    """Return the global tkwant MPI communicator if input `comm` is None"""
    if comm is None:
        if _COMM is None:
            communicator_init()
        comm = _COMM
    return comm


def round_robin(comm, key):
    """Schedule integer keys in a round robin fashion to the MPI ranks.

    comm : `mpi4py.MPI.Intracomm`
        The MPI communicator.
    key : int
        Integer key.

    Returns
    -------
    run : bool
        ``run`` is true if rank == key + m * size , where m is an arbitrary
        integer, and size and rank correspond to the MPI size and rank.
    """
    return comm.rank == key % comm.size


def distribute_dict(input_dict, distribute_keys, comm):
    """Distribute a dict over all MPI ranks.

    input_dict : dict
        A dictionary that is identical on each MPI rank.
    distribute_keys : callable
        Boolean function with signature `(key, comm)` that maps each key
        from ``input_dict`` exactly to one MPI rank.
    comm : `mpi4py.MPI.Intracomm`
        The MPI communicator.

    Returns
    -------
    distributed_dict : dict
        A dict which distributed over all MPI ranks.
    """
    return {key: value for key, value in input_dict.items()
            if distribute_keys(comm, key)}


def _get_data_per_rank(data, comm, rank=None):
    """Get the data distributed over all MPI ranks.

    Notes
    -----
    If rank is None, we return a list, each list index corresponds to the
    MPI rank and the content to the data on that specific rank.
    If rank is set, we return the data on that specific rank.
    """
    if rank is None:
        data_per_rank = comm.allgather(data)
    else:
        assert 0 <= rank < comm.size
        data_per_rank = comm.bcast(data, root=rank)
    return data_per_rank


class DistributedDict():
    """A class to handle a dictionary which is distributed over MPI ranks."""

    def __init__(self, data=None, comm=None):
        """
        Initialize the dictionary.

        Parameters
        ----------
        data : dict, optional
            Dictionary with all initial one-body states.
            The dictionary can (and should be) distributed over all MPI ranks.
        comm : `mpi4py.MPI.Intracomm`, optional
            The MPI communicator over which to parallelize the computation.
            By default, use the tkwant global MPI communicator.
        """
        self.comm = get_communicator(comm)
        if data is None:
            data = {}
        self._data = data
        if not self.keys_are_unique():
            raise ValueError('Keys in input dict are dublicated')

    def add(self, key, value, rank=None, check=True):
        """Add a key value pair to the dictionary"""
        if check:
            if self.key_is_present(key):
                raise ValueError('Cannot add, key={} already present'.format(key))
        if rank is None:
            size_per_rank = self.size()
            rank = np.argmin(size_per_rank)
        if not 0 <= rank < self.comm.size:
            raise ValueError('0 <= rank < {} required, but rank={}'.
                             format(self.comm.size, rank))
        if self.comm.rank == rank:
            self._data.update({key: value})

    def delete(self, key):
        """Delete a dictionary entry"""
        if self.comm.rank == self.rank_from_key(key):
            del self._data[key]

    def data(self, key):
        """Get the data corresponding to the key"""
        data = self._data.get(key)
        rank = self.rank_from_key(key)
        return self.comm.bcast(data, root=rank)

    def local_data(self):
        """Get all data stored on the local MPI ranks"""
        return self._data

    def local_keys(self):
        """Get all keys on the local MPI ranks"""
        return list(self._data.keys())

    def keys(self, rank=None):
        """Get all keys of the dictionary"""
        my_keys = list(self._data.keys())
        keys_per_rank = _get_data_per_rank(my_keys, self.comm, rank)
        if rank is None:  # flatten data to one list
            return [y for x in keys_per_rank for y in x]
        return keys_per_rank

    def size(self, rank=None):
        """Get the size of the dictonary"""
        size = len(self._data)
        return np.array(_get_data_per_rank(size, self.comm, rank))

    def move_data(self, key, to_rank):
        """Move the data to a specific MPI rank"""
        rank = self.rank_from_key(key)
        if self.comm.rank == rank:
            self.comm.send(self._data[key], dest=to_rank, tag=44)
            del self._data[key]
        if self.comm.rank == to_rank:
            self._data[key] = self.comm.recv(source=rank, tag=44)

    def rank_from_key(self, key):
        """Get the MPI rank that hosts a specific key data"""
        for rank in range(self.comm.size):
            if key in self.keys(rank=rank):
                return rank
        raise ValueError('Cannot find key={}'.format(key))

    def key_is_present(self, key):
        """Returns true if a key is present in the dataset"""
        try:
            self.rank_from_key(key)
        except ValueError:
            return False
        return True

    def keys_are_unique(self):
        """Returns true the stored dictionary data is not dublicated on MPI ranks"""
        keys = self.keys()
        if len(set(list(keys))) == len(keys):
            return True
        return False
