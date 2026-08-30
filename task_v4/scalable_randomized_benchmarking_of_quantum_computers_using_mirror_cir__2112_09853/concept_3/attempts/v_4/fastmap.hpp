struct FastMap {
  array<Bits,40> base{};
  vector<Bits> first,second,alpha,beta;
  array<array<array<uint8_t,4>,120>,120> cross{};
  static int symplectic(Bits left,Bits right) {return __builtin_parityll((left&(right>>nq))^((left>>nq)&right));}
  FastMap(const Circuit &circuit) {
    for(int index=0;index<2*nq;index++)base[index]=1ULL<<index;
    for(auto &layer:circuit.layers) {
      for(int qubit=0;qubit<nq;qubit++)for(char gate:words[layer.local[qubit]]) {
        if(gate=='H')swap(base[qubit],base[nq+qubit]);else if(gate=='S')base[qubit]^=base[nq+qubit];
      }
      for(auto [control,target]:layer.cx) {first.push_back(base[target]);second.push_back(base[nq+control]);base[control]^=base[target];base[nq+target]^=base[nq+control];}
    }
    alpha.resize(first.size());beta.resize(first.size());
    for(int gate=0;gate<(int)first.size();gate++) {
      for(int index=0;index<2*nq;index++) {alpha[gate]|=Bits(symplectic(base[index],second[gate]))<<index;beta[gate]|=Bits(symplectic(base[index],first[gate]))<<index;}
      for(int previous=gate+1;previous<(int)first.size();previous++) {
        cross[gate][previous]={uint8_t(symplectic(first[previous],second[gate])),uint8_t(symplectic(second[previous],second[gate])),uint8_t(symplectic(first[previous],first[gate])),uint8_t(symplectic(second[previous],first[gate]))};
      }
    }
  }
  void columns(array<int,3> omitted,Bits *result) const {
    copy(base.begin(),base.begin()+2*nq,result);Bits alphas[3]={},betas[3]={};
    for(int position=2;position>=0;position--) {
      int gate=omitted[position];if(gate<0)continue;Bits currentalpha=alpha[gate],currentbeta=beta[gate];
      for(int previous=position+1;previous<3;previous++)if(omitted[previous]>=0) {
        auto factors=cross[gate][omitted[previous]];
        if(factors[0])currentalpha^=alphas[previous];if(factors[1])currentalpha^=betas[previous];
        if(factors[2])currentbeta^=alphas[previous];if(factors[3])currentbeta^=betas[previous];
      }
      alphas[position]=currentalpha;betas[position]=currentbeta;
      while(currentalpha){int index=__builtin_ctzll(currentalpha);currentalpha&=currentalpha-1;result[index]^=first[gate];}
      while(currentbeta){int index=__builtin_ctzll(currentbeta);currentbeta&=currentbeta-1;result[index]^=second[gate];}
    }
  }
};
