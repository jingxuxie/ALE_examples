int cmc_step(){

	// Check for calling of function
	if(err::check==true) std::cout << "montecarlo::ConstrainedMonteCarlo has been called" << std::endl;

	// check for cmc initialisation
	if(cmc::is_initialised==false) CMCinit();

	int atom_number1;
	int atom_number2;
	int imat1;
	int imat2;

	double delta_energy1;
	double delta_energy2;
	double delta_energy21;

	double Eold;
	double Enew;

	std::vector<double> spin1_initial(3);
	std::vector<double> spin1_final(3);
	double spin2_initial[3];
	double spin2_final[3];

	double spin1_init_mvd[3];
	double spin1_fin_mvd[3];
	double spin2_init_mvd[3];
	double spin2_fin_mvd[3];

	double M_other[3];
	double Mz_old;
	double Mz_new;

	double probability;

   // Material dependent temperature rescaling
   std::vector<double> rescaled_material_kBTBohr(mp::num_materials);
   std::vector<double> sigma_array(mp::num_materials); // range for tuned gaussian random move
   for(int m=0; m<mp::num_materials; ++m){
      double alpha = mp::material[m].temperature_rescaling_alpha;
      double Tc = mp::material[m].temperature_rescaling_Tc;
      double rescaled_temperature = sim::temperature < Tc ? Tc*pow(sim::temperature/Tc,alpha) : sim::temperature;
      rescaled_material_kBTBohr[m] = 9.27400915e-24/(rescaled_temperature*1.3806503e-23);
      sigma_array[m] = rescaled_temperature < 1.0 ? 0.02 : pow(1.0/rescaled_material_kBTBohr[m],0.2)*0.08;
   }

	// copy matrices for speed
	double ppolar_vector[3];
	double ppolar_matrix[3][3];
	double ppolar_matrix_tp[3][3];

	for (int i=0;i<3;i++){
		ppolar_vector[i]=cmc::polar_vector[0][i];
		for (int j=0;j<3;j++){
			ppolar_matrix[i][j]=cmc::polar_matrix[i][j];
			ppolar_matrix_tp[i][j]=cmc::polar_matrix_tp[i][j];
		}
	}

	//sigma = ((kbT_bohr)**0.2)*0.08_dp
	//inv_kbT_bohr = 1.0_dp/kbT_bohr

	M_other[0] = 0.0;
	M_other[1] = 0.0;
	M_other[2] = 0.0;

	for(int atom=0;atom<atoms::num_atoms;atom++){
		const double mu = atoms::m_spin_array[atom];
		M_other[0] = M_other[0] + atoms::x_spin_array[atom] * mu; //multiplied by polar_vector below
		M_other[1] = M_other[1] + atoms::y_spin_array[atom] * mu;
		M_other[2] = M_other[2] + atoms::z_spin_array[atom] * mu;
	}

	double statistics_reject = 0.0; // counter for number of rejected moves (for adaptive algorothm)

	for (int mcs=0;mcs<atoms::num_atoms;mcs++){
		// Randomly select spin number 1
		atom_number1 = int(mtrandom::grnd()*atoms::num_atoms);
		imat1=atoms::type_array[atom_number1];

		// get spin moment for atom 1
		const double mu1 = atoms::m_spin_array[atom_number1];

      internal::delta_angle=sigma_array[imat1];

		// Save initial Spin 1
		spin1_initial[0] = atoms::x_spin_array[atom_number1];
		spin1_initial[1] = atoms::y_spin_array[atom_number1];
		spin1_initial[2] = atoms::z_spin_array[atom_number1];

		//spin1_init_mvd = matmul(polar_matrix, spin1_initial)
		spin1_init_mvd[0]=ppolar_matrix[0][0]*spin1_initial[0]+ppolar_matrix[0][1]*spin1_initial[1]+ppolar_matrix[0][2]*spin1_initial[2];
		spin1_init_mvd[1]=ppolar_matrix[1][0]*spin1_initial[0]+ppolar_matrix[1][1]*spin1_initial[1]+ppolar_matrix[1][2]*spin1_initial[2];
		spin1_init_mvd[2]=ppolar_matrix[2][0]*spin1_initial[0]+ppolar_matrix[2][1]*spin1_initial[1]+ppolar_matrix[2][2]*spin1_initial[2];

      // Make Monte Carlo move
      montecarlo::internal::mc_move(spin1_initial,spin1_final);

		//spin1_fin_mvd = matmul(polar_matrix, spin1_final)
		spin1_fin_mvd[0]=ppolar_matrix[0][0]*spin1_final[0]+ppolar_matrix[0][1]*spin1_final[1]+ppolar_matrix[0][2]*spin1_final[2];
		spin1_fin_mvd[1]=ppolar_matrix[1][0]*spin1_final[0]+ppolar_matrix[1][1]*spin1_final[1]+ppolar_matrix[1][2]*spin1_final[2];
		spin1_fin_mvd[2]=ppolar_matrix[2][0]*spin1_final[0]+ppolar_matrix[2][1]*spin1_final[1]+ppolar_matrix[2][2]*spin1_final[2];

		// Calculate Energy Difference 1
		//call calc_one_spin_energy(delta_energy1,spin1_final,atom_number1)

		// Calculate current energy
		Eold = sim::calculate_spin_energy(atom_number1);

		// Copy new spin position (provisionally accept move)
		atoms::x_spin_array[atom_number1] = spin1_final[0];
		atoms::y_spin_array[atom_number1] = spin1_final[1];
		atoms::z_spin_array[atom_number1] = spin1_final[2];

		// Calculate new energy
		Enew = sim::calculate_spin_energy(atom_number1);

		// Calculate difference in Joules/mu_B
		delta_energy1 = (Enew-Eold)*mp::material[imat1].mu_s_SI*1.07828231e23; //1/9.27400915e-24

		// Compute second move

		// Randomly select spin number 2 (i/=j)
		atom_number2 = int(mtrandom::grnd()*atoms::num_atoms);
		imat2=atoms::type_array[atom_number2];
      // get spin moment for atom 2
      const double mu2 = atoms::m_spin_array[atom_number2];

		// Save initial Spin 2
		spin2_initial[0] = atoms::x_spin_array[atom_number2];
		spin2_initial[1] = atoms::y_spin_array[atom_number2];
		spin2_initial[2] = atoms::z_spin_array[atom_number2];

		//spin2_init_mvd = matmul(polar_matrix, spin2_initial)
		spin2_init_mvd[0]=ppolar_matrix[0][0]*spin2_initial[0]+ppolar_matrix[0][1]*spin2_initial[1]+ppolar_matrix[0][2]*spin2_initial[2];
		spin2_init_mvd[1]=ppolar_matrix[1][0]*spin2_initial[0]+ppolar_matrix[1][1]*spin2_initial[1]+ppolar_matrix[1][2]*spin2_initial[2];
		spin2_init_mvd[2]=ppolar_matrix[2][0]*spin2_initial[0]+ppolar_matrix[2][1]*spin2_initial[1]+ppolar_matrix[2][2]*spin2_initial[2];

		// Calculate new spin based on constraint Mx=My=0
		const double mom_ratio = (mu1/mu2);
		spin2_fin_mvd[0] = mom_ratio*(spin1_init_mvd[0]-spin1_fin_mvd[0]) + spin2_init_mvd[0];
		spin2_fin_mvd[1] = mom_ratio*(spin1_init_mvd[1]-spin1_fin_mvd[1]) + spin2_init_mvd[1];

		if(((spin2_fin_mvd[0]*spin2_fin_mvd[0]+spin2_fin_mvd[1]*spin2_fin_mvd[1])<1.0) && (atom_number1 != atom_number2)){

			spin2_fin_mvd[2] = vmath::sign(spin2_init_mvd[2])*sqrt(1.0-spin2_fin_mvd[0]*spin2_fin_mvd[0] - spin2_fin_mvd[1]*spin2_fin_mvd[1]);

			//spin2_final = matmul(polar_matrix_tp, spin2_fin_mvd)
			spin2_final[0]=ppolar_matrix_tp[0][0]*spin2_fin_mvd[0]+ppolar_matrix_tp[0][1]*spin2_fin_mvd[1]+ppolar_matrix_tp[0][2]*spin2_fin_mvd[2];
			spin2_final[1]=ppolar_matrix_tp[1][0]*spin2_fin_mvd[0]+ppolar_matrix_tp[1][1]*spin2_fin_mvd[1]+ppolar_matrix_tp[1][2]*spin2_fin_mvd[2];
			spin2_final[2]=ppolar_matrix_tp[2][0]*spin2_fin_mvd[0]+ppolar_matrix_tp[2][1]*spin2_fin_mvd[1]+ppolar_matrix_tp[2][2]*spin2_fin_mvd[2];

			// Automatically accept move for Spin1 - now before if ^^
			//atomic_spin_array(:,atom_number1) = spin1_final(:)

			//Calculate Energy Difference 2
			// Calculate current energy
			Eold = sim::calculate_spin_energy(atom_number2);

			// Copy new spin position (provisionally accept move)
			atoms::x_spin_array[atom_number2] = spin2_final[0];
			atoms::y_spin_array[atom_number2] = spin2_final[1];
			atoms::z_spin_array[atom_number2] = spin2_final[2];

			// Calculate new energy
			Enew = sim::calculate_spin_energy(atom_number2);

			// Calculate difference in Joules/mu_B
			delta_energy2 = (Enew-Eold)*mp::material[imat2].mu_s_SI*1.07828231e23; //1/9.27400915e-24

			// Calculate Delta E for both spins
			delta_energy21 = delta_energy1*rescaled_material_kBTBohr[imat1] + delta_energy2*rescaled_material_kBTBohr[imat2];

			// Compute Mz_other, Mz, Mz'
			Mz_old = M_other[0]*ppolar_vector[0] + M_other[1]*ppolar_vector[1] + M_other[2]*ppolar_vector[2];

			Mz_new = (M_other[0] + mu1*spin1_final[0] + mu2*spin2_final[0]- mu1*spin1_initial[0] - mu2*spin2_initial[0])*ppolar_vector[0] +
						(M_other[1] + mu1*spin1_final[1] + mu2*spin2_final[1]- mu1*spin1_initial[1] - mu2*spin2_initial[1])*ppolar_vector[1] +
						(M_other[2] + mu1*spin1_final[2] + mu2*spin2_final[2]- mu1*spin1_initial[2] - mu2*spin2_initial[2])*ppolar_vector[2];

			// Check for lower energy state and accept unconditionally
			//if((delta_energy21<0.0) && (Mz_new>0.0)) continue;

			// Otherwise evaluate probability for move
			//else{
				// If move is favorable then accept
				probability = exp(-delta_energy21)*((Mz_new/Mz_old)*(Mz_new/Mz_old))*std::fabs(spin2_init_mvd[2]/spin2_fin_mvd[2]);
				if((probability>=mtrandom::grnd()) && (Mz_new>0.0) ){
					M_other[0] = M_other[0] + mu1*spin1_final[0] + mu2*spin2_final[0] - mu1*spin1_initial[0] - mu2*spin2_initial[0];
					M_other[1] = M_other[1] + mu1*spin1_final[1] + mu2*spin2_final[1] - mu1*spin1_initial[1] - mu2*spin2_initial[1];
					M_other[2] = M_other[2] + mu1*spin1_final[2] + mu2*spin2_final[2] - mu1*spin1_initial[2] - mu2*spin2_initial[2];
					cmc::mc_success += 1.0;
				}
				//if both p1 and p2 not allowed then
				else{
					// reset spin positions
					atoms::x_spin_array[atom_number1] = spin1_initial[0];
					atoms::y_spin_array[atom_number1] = spin1_initial[1];
					atoms::z_spin_array[atom_number1] = spin1_initial[2];

					atoms::x_spin_array[atom_number2] = spin2_initial[0];
					atoms::y_spin_array[atom_number2] = spin2_initial[1];
					atoms::z_spin_array[atom_number2] = spin2_initial[2];

					cmc::energy_reject += 1.0;
					statistics_reject += 1.0;
				}
			//}
		}
		// if s2 not on unit sphere
		else{
			atoms::x_spin_array[atom_number1] = spin1_initial[0];
			atoms::y_spin_array[atom_number1] = spin1_initial[1];
			atoms::z_spin_array[atom_number1] = spin1_initial[2];
			cmc::sphere_reject+=1.0;
			statistics_reject += 1.0;
		}

		cmc::mc_total += 1.0;
	}

	// calculate new adaptive step sigma angle
	if(montecarlo::algorithm == montecarlo::adaptive){
		const double statistics_moves = atoms::num_atoms;
		const double last_rejection_rate = statistics_reject / statistics_moves;
		const double factor = 0.5 / last_rejection_rate;
		montecarlo::internal::adaptive_sigma *= factor;
		// check for excessive range (too small angle takes too long to grow, too large does not improve performance) and truncate
		if (montecarlo::internal::adaptive_sigma > 60.0 || montecarlo::internal::adaptive_sigma < 1e-5) montecarlo::internal::adaptive_sigma = 60.0;
	}

	return EXIT_SUCCESS;
}
