from placement.instance_scatter import scatter_instances
from placement.factory import AssetFactory, make_asset_collection

from util.random import random_general as rg
from surfaces.scatters.utils.wind import wind

def apply(obj, selection=None, density=('uniform', 1, 6), **kwargs):

    fern_col = make_asset_collection(FernFactory(np.random.randint(1e5)), n=2, verbose=True)
    scatter_obj = scatter_instances(
        base_obj=obj, collection=fern_col,
        scale=0.7, scale_rand=0.7, scale_rand_axi=0.3,
        vol_density=rg(density),
        normal_fac=0.3, 
        rotation_offset=wind(strength=10),
        selection=selection
    )
