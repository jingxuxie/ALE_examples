![Package-X](https://mule-tools.gitlab.io/package-x/PackageXLogo.png)

Package X was developed by [Hiren Patel](https://web.archive.org/web/20211204195428/http://hhpatel.net/) [[1503.01469](https://arxiv.org/abs/1503.01469), [1612.00009](https://arxiv.org/abs/1612.00009)].
All credit for the original code goes to him and we would like to take this opportunity to thank Hiren for his great work!

If you are using Package X, please cite Hiren's papers

> H. H. Patel, <br/>
> *Package-X: A Mathematica package for the analytic calculation of one-loop integrals*, <br/>
> [Comput. Phys. Commun. **197** (2015), 276-290](https://doi.org/10.1016/j.cpc.2015.08.017), <br/>
> [[arXiv:1503.01469](https://arxiv.org/abs/1503.01469)].
>
> H. H. Patel, <br/>
> *Package-X 2.0: A Mathematica package for the analytic calculation of one-loop integrals*, <br/>
> [Comput. Phys. Commun. **218** (2017), 66-70](https://doi.org/10.1016/j.cpc.2015.08.017), <br/>
> [[1612.00009](https://arxiv.org/abs/1612.00009)].

If you have questions about this website, contact [yannick.ulrich@liverpool.ac.uk](mailto:yannick.ulrich@liverpool.ac.uk).

## About Package X
*Taken from the original website*

Calculating Feynman loop integrals commonly encountered in nuclear physics, particle physics and cosmology is a time consuming task that takes weeks and sometimes months to complete by hand.
Extensively tested and adopted by researchers around the world, Package‑X is the definitive Mathematica program to instantly solve one loop Feynman integrals in full generality.

### Technical features
* Computes dimensionally regulated one-loop integrals with up to four distinct propagators of arbitrarily high rank.
* Calculates traces of Dirac matrices in *d* dimensions for closed fermion loops, or carries out Dirac algebra for open fermion lines
* Generates analytic results for any kinematic configuration (e.g. at zero external momentum, at physical threshold, etc.) for real masses and external invariants.
* Provides analytic expressions for UV-divergent, IR-divergent and finite parts either separately or all together.
* Computes discontinuities across cuts of one-loop integrals.
* Constructs Taylor series expansions for one-loop integrals.
* Evaluates with either machine precision or arbitrary precision arithmetic, and is always consistent with the +*i&epsilon;* prescription.

### User interface features
* Complete documentation within the Wolfram Documentation Center which includes
    * over 350 basic usage examples with detailed information for every symbol defined by Package‑X,
    * 4 project-scale tutorials,
    * and instructions on linking Package‑X to FeynCalc, LoopTools, and the COLLIER library.
* Readable and intuitive input
* Output easily manipulatable and readily numerically evaluatable
* Command-line friendly


## Third party software

Some authors have developed additional tools to be used with Package-X.
We try to collect some here

 * [AmpTools](https://gitlab.com/Fionq/amptools) by [Fiona Kirk](https://inspirehep.net/authors/2819661) to convert FeynArts to Package-X
 * QGraf interface by the McMule Collaboration (to be release soon)

*Note*: if you have developed any third party software and want us to link it here, please get in touch.


## Downloads

<table>
    <thead>
        <tr>
            <th>Package</th>
            <th>License</th>
            <th>Legacy version</th>
            <th>Most recent source code (packaged)</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>Package-X</td>
            <td>CC-BY-4.0</td>
            <td><a href="https://mule-tools.gitlab.io/package-x/downloads/X-2.1.1-patched-2.zip">v2.1.1-patched-2</a></td>
            <td>
                <a href="https://mule-tools.gitlab.io/package-x/downloads/X-master.zip">zip</a>
                <a href="https://mule-tools.gitlab.io/package-x/downloads/X-master.tar.gz">tar.gz</a>
            </td>
        </tr>
        <tr>
            <td>CollierLink</td>
            <td>GPLv3</td>
            <td><a href="https://mule-tools.gitlab.io/package-x/downloads/CollierLink-1.0.1.zip">v1.0.1</a></td>
            <td>
                not yet available
            </td>
        </tr>
        <tr>
            <td>PVReduce</td>
            <td>CC-BY-4.0</td>
            <td><a href="https://mule-tools.gitlab.io/package-x/downloads/PVReduce-v0.1.0.tar.gz">v0.1.0</a></td>
            <td>
                <a href="https://mule-tools.gitlab.io/package-x/downloads/PVReduce-master.zip">zip</a>
                <a href="https://mule-tools.gitlab.io/package-x/downloads/PVReduce-master.tar.gz">tar.gz</a>
            </td>
        </tr>
    </tbody>
</table>

## Documentation
Hiren Patel wrote a fabulous primer explaining how to use Package-X.
You can find a copy [here](https://mule-tools.gitlab.io/package-x/downloads/primer.pdf).
Further, there is a detailed built-in documentation in the *Wolfram Documentation Center*.

### Installation Instructions
Uncompress downloaded file, and copy the Package‑X folder (`/X`) with all its contents to the folder `$UserBaseDirectory/Applications/`.
See the primer for details.

### Expansion packs
We provide the official extension packs CollierLink and PVReduce (see above).
Unfortunately, we do not have a copy of TensorD.
If you have one and are willing to share it, please contact [yannick.ulrich@liverpool.ac.uk](mailto:yannick.ulrich@liverpool.ac.uk).
Future extension packs developed independently of Hiren Patel may be shared later.

To install an expansion pack, uncompress the downloaded file, and copy the directory with all its contents to the folder `$UserBaseDirectory/Applications/` (but not inside the Package‑X directory itself).


#### CollierLink
Interface to the COLLIER library for rapid numerical evaluation of Passarino-Veltman functions

* CollierLink now uses version 1.2 of the COLLIER library.
* Improved library dependency issues on macOS and Linux.
* Fixed minor bugs caused by certain C compilers.

We have the [source code for CollierLink](https://gitlab.com/mule-tools/package-x/-/tree/root/CollierLink) as well as compilation instructions for Linux.
In the near future, we will also provide up-to-date binaries for macOS.

#### PVReduce
Reduce Passarino-Veltman functions to scalar functions without limiting to 4 dimensions, and without inserting explicit formulae.

PVReduce was never publicly available but is still licensed under CC-BY-4.0.


## Why this page?

At or around 1 July, Hiren Patel took down the official website (archived version [here](http://web.archive.org/web/20220619174704/https://packagex.hepforge.org/)).
The code is still available on the [CPC/Mendeley website](https://data.mendeley.com/datasets/yfkwrd4d5t).

Since Package-X and companion tools are widely used, both by us and others, it would be great loss to the community of it was no longer accessible.
Hence, we chose to re-publish the code here since it was licensed under CC-BY-4.0 (core Package-X and PVReduce) and GPLv3 (CollierLink).

Package-X was originally distributed in the Encode format of Mathematica.
To facilitate further development, fix bugs and add new features, we also provide the [source code](https://gitlab.com/mule-tools/package-x).
