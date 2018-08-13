# Copyright 2014-2018 The PySCF Developers. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import print_function, division

def kmat_den(mf, dm=None, algo=None, **kw):
  """
  Computes the matrix elements of Fock exchange operator
  Args:
    mf : (System Variables), this must have arrays of coordinates and species, etc
  Returns:
    matrix elements
  """
  from scipy.sparse import csr_matrix
  import numpy as np
  from numpy import einsum 

  pb,hk=mf.add_pb_hk(**kw)
  dm = mf.make_rdm1() if dm is None else dm

  n = mf.norbs
  if mf.nspin==1:
    dm = dm.reshape((n,n))
  elif mf.nspin==2:
    dm = dm.reshape((mf.nspin,n,n))
  else:
    print(nspin)
    raise RuntimeError('nspin>2?')
    
  algol = algo.lower() if algo is not None else 'ac_vertex_fm'

  if algol=='fci':
    mf.fci_den = abcd2v = mf.fci_den if hasattr(mf, 'fci_den') else pb.comp_fci_den(hk)
    kmat = einsum('abcd,...bc->...ad', abcd2v, dm)
  elif algol=='ac_vertex_fm':
    pab2v = pb.get_ac_vertex_array()
    pcd = einsum('pq,qcd->pcd', hk, pab2v)
    pac = einsum('pab,...bc->...pac', pab2v, dm)
    kmat = einsum('...pac,pcd->...ad', pac, pcd)
  elif algol=='dp_vertex_fm':
    dab2v = pb.get_dp_vertex_array()
    da2cc = pb.get_da2cc_den()
    dq2v  = einsum('dp,pq->dq', da2cc, hk)
    pcd   = einsum('dq,dab->qab', dq2v, dab2v)
    dac   = einsum('dab,...bc->...dac', dab2v, dm)
    pac   = einsum('...dac,dp->...pac', dac, da2cc)
    kmat  = einsum('...pac,pcd->...ad', pac, pcd)
  elif algol=='dp_vertex_loops_fm':
    dab2v = pb.get_dp_vertex_array()
    da2cc = pb.get_da2cc_den()
    dq2v  = einsum('dp,pq->dq', da2cc, hk)
    kmat  = np.zeros_like(dm)
    for d in range(n):
      pc2   = einsum('dq,da->qa', dq2v, dab2v[:,:,d])
      for a in range(n):
        dc  = einsum('db,...bc->...dc', dab2v[:,a,:], dm)
        pc1  = einsum('...dc,dp->...pc', dc, da2cc)
        kmat[...,a,d]  = einsum('...pc,pc->...', pc1, pc2)
  else:
    print('algo=', algo)
    raise RuntimeError('unknown algorithm')

  return kmat

