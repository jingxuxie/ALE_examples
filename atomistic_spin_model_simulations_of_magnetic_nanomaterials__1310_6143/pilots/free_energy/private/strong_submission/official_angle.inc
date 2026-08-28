void mc_angle(const std::vector<double>& old_spin, std::vector<double>& new_spin, const double angle){

   new_spin[0] = old_spin[0] + mtrandom::gaussian() * angle;
   new_spin[1] = old_spin[1] + mtrandom::gaussian() * angle;
   new_spin[2] = old_spin[2] + mtrandom::gaussian() * angle;

   // Calculate new spin length
   const double r = 1.0/sqrt (new_spin[0]*new_spin[0]+new_spin[1]*new_spin[1]+new_spin[2]*new_spin[2]);

   // Apply normalisation
   new_spin[0] *= r;
   new_spin[1] *= r;
   new_spin[2] *= r;

   return;

}
