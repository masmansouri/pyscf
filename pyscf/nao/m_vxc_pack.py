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
import numpy as np
from numpy import array, int64, zeros, float64
try:
    import numba as nb
    from pyscf.nao.m_numba_utils import fill_triu_v2
    use_numba = True
except:
    use_numba = False

#
#
#
def vxc_pack(self, **kw):
  """
    Computes the exchange-correlation matrix elements packed version (upper triangular)
    Args:
      sv : (System Variables), this must have arrays of coordinates and species, etc
    Returns:
      vxc,exc
  """
  from pyscf.nao.m_xc_scalar_ni import xc_scalar_ni
  from pyscf.nao.m_ao_matelem import ao_matelem_c

  #sv, dm, xc_code, deriv, kernel=None, ao_log=None, dtype=float64, **kvargs
  sv = self
  dm = kw['dm'] if 'dm' in kw else self.make_rdm1()
  kernel = kw['kernel'] if 'kernel' in kw else None
  ao_log = kw['ao_log'] if 'ao_log' in kw else self.ao_log
  xc_code = kw['xc_code'] if 'xc_code' in kw else self.xc_code
  kw.pop('xc_code',None)
  dtype = kw['dtype'] if 'dtype' in kw else float64

  aome = ao_matelem_c(ao_log.rr, ao_log.pp, sv, dm)
  me = aome.init_one_set(ao_log)
  atom2s = zeros((sv.natm+1), dtype=int64)
  for atom,sp in enumerate(sv.atom2sp): atom2s[atom+1]=atom2s[atom]+me.ao1.sp2norbs[sp]
  sp2rcut = array([max(mu2rcut) for mu2rcut in me.ao1.sp_mu2rcut])
  norbs = atom2s[-1]

  #ind = triu_indices(norbs)
  if kernel is None: 
    kernel = zeros(( (self.nspin-1)*2+1, norbs*(norbs+1)//2), dtype=dtype )

  if np.any(kernel.shape!=((self.nspin-1)*2+1, int(norbs*(norbs+1)//2))):
    print(__name__, 'kernel.shape       ', kernel.shape)
    print('(self.nspin-1)*2+1 ', (self.nspin-1)*2+1      )
    print('norbs*(norbs+1)//2 ', int(norbs*(norbs+1)//2) )
    raise ValueError("wrong dimension for kernel")

  for atom1,[sp1,rv1,s1,f1] in enumerate(zip(sv.atom2sp,sv.atom2coord,atom2s,atom2s[1:])):
    for atom2,[sp2,rv2,s2,f2] in enumerate(zip(sv.atom2sp,sv.atom2coord,atom2s,atom2s[1:])):
      if atom2>atom1: continue
      if (sp2rcut[sp1]+sp2rcut[sp2])**2<=sum((rv1-rv2)**2) : continue
      
      iab2block = xc_scalar_ni(me,sp1,rv1,sp2,rv2,xc_code=xc_code,**kw)
      
      if use_numba:
        for i,ab2v in enumerate(iab2block):
          fill_triu_v2(ab2v, kernel[i], s1, f1, s2, f2, norbs, add=True)
      else:
        for i,ab2v in enumerate(iab2block):
          for i1 in range(s1,f1):
            for i2 in range(s2, min(i1+1, f2)):
              ind = 0
              if i2 > 0:
                for beta in range(1, i2+1):
                  ind += norbs -beta
              ind += i1
              kernel[i,ind] += xc[i1-s1,i2-s2]
               
  return kernel
