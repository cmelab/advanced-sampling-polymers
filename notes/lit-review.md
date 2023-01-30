# Parallel Tempering:
## Papers
### Parallel Tempering: Theory, Applications, and New Perspectives
- doi: https://arxiv.org/pdf/physics/0508111.pdf
- Authors: Earl, Deem
- Outstanding issues and questions:
	- Some questions around information/replica exchange details
	- How long should you sample at the altered T/epsilon before swapping?
	- What range of T/epsilon should you use?
	- How long to spend samping after the replica exchange?

- They mention that temperature isn't always the best parameter to temper
- They mention you can also temper the pair potentials
- Using this approach with MD, we need to be mindful of particle momenta after an exchange occurs
- One suggestion is below, but they also mention having an acceptange criteria for an exchange

	$p(i)_{new} = \sqrt\dfrac{T_{new}}{T_{old}}p(i)_{old}$

- This might be something Hoomd can already do for us when randomize velocities
- Note about energy histograms required to overlap for swaps to be accepted
- They mention a paper from Fukunishi (https://aip.scitation.org/doi/10.1063/1.1472510)
	- I think this paper uses a similar approach to altering LJ parameters
	- They alter the cut off value used, and if small enough, let particles move through each other

### Parallel excluded volume tempering for polymer melts
- doi: https://journals.aps.org/pre/abstract/10.1103/PhysRevE.63.016701
- Authors: Bunker, Dunweg
- 
	

## Thoughts and Brainstorming
	- Seems the general algorithm is this:
		- Sample a system at some altered values of T or epsilon
		- Create a "replica exhange" by using this sytem's configuration to sample at values of T/epsilon of interest.
	- I'm a little confused about the Earl and Deem paper's talk of accepting or rejecting replica swaps in the MD section
	- Maybe the point to take away is that we need to be careful in how we set up swaps (e.g. progression of T or epsilon)	
