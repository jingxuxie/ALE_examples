#include <algorithm>
#include <cmath>
#include <cstdint>
#include <numeric>
#include <random>
#include <vector>

struct Sampler {
    int edges, pairs, observations, family, anchors, minimum, maximum, active, anchor;
    int cross_start, spam_start, drift_start, dimension;
    const int *pair_edges;
    const double *design, *depth, *successes, *shots, *context, *odds;
    double *state;
    double floor;
    double temperature;
    std::mt19937_64 random;
    std::vector<std::vector<int>> edge_rows, pair_rows;
    std::vector<double> rate, latent, likelihood, size, anchor_score;
    std::vector<std::vector<int>> neighbors;
    double pair_weight_sum;
    double nodes[7] = {0.0254460438286207, 0.129234407200303, 0.297077424311301, 0.5,
                       0.702922575688699, 0.870765592799697, 0.974553956171379};
    double weights[7] = {0.064742483084435, 0.139852695744638, 0.190915025252559,
                         0.208979591836735, 0.190915025252559, 0.139852695744638, 0.064742483084435};

    double uniform() { return std::generate_canonical<double, 53>(random); }
    bool accept(double difference) { return std::log(uniform()) < difference; }

    double prior_odds(int pair) {
#ifdef IMPROVED_PRIOR
        if (family == 2) {
            double separation=0.022-state[1+pair_edges[2*pair]]-state[1+pair_edges[2*pair+1]];
            double expected=minimum+1.5;
            return std::log(expected/(1-expected/pairs)*separation*separation/pair_weight_sum);
        }
#endif
        return odds[anchor*pairs+pair];
    }

    void anticorrelated_base(int edge, double proposal) {
        double difference=proposal-state[1+edge];
        double new_weight_sum=pair_weight_sum;
        double score=0;
        std::vector<double> changes(observations,0.0);
        for (int row:edge_rows[edge]) changes[row]=difference;
        for (int pair=0; pair<pairs; ++pair) {
            if (pair_edges[2*pair]!=edge && pair_edges[2*pair+1]!=edge) continue;
            double separation=0.022-state[1+pair_edges[2*pair]]-state[1+pair_edges[2*pair+1]];
            new_weight_sum+=(separation-difference)*(separation-difference)-separation*separation;
            if (state[cross_start+pair]>0) {
                score+=2*std::log((separation-difference)/separation);
                for (int row:pair_rows[pair]) changes[row]-=0.5*difference;
            }
        }
        score-=active*std::log(new_weight_sum/pair_weight_sum);
        for (int row:edge_rows[edge])
            score+=log_likelihood(row,rate[row]+changes[row],latent[row])-likelihood[row];
        if (accept(score)) {
            state[1+edge]=proposal;
            pair_weight_sum=new_weight_sum;
            for (int pair=0; pair<pairs; ++pair)
                if (state[cross_start+pair]>0 && (pair_edges[2*pair]==edge || pair_edges[2*pair+1]==edge))
                    state[cross_start+pair]-=0.5*difference;
            for (int row:edge_rows[edge]) {
                rate[row]+=changes[row];
                likelihood[row]=log_likelihood(row,rate[row],latent[row]);
            }
        }
    }

    void swap_updates() {
        std::vector<int> included;
        for (int pair=0; pair<pairs; ++pair) if (state[cross_start+pair]>0) included.push_back(pair);
        std::vector<double> changes(observations);
        for (int attempt=0; attempt<2*active; ++attempt) {
            int position=random()%included.size();
            int old_pair=included[position];
            bool local=attempt%2;
            int new_pair=local ? neighbors[old_pair][random()%neighbors[old_pair].size()] : random()%pairs;
            if (state[cross_start+new_pair]>0) continue;
            double score=prior_odds(new_pair)-prior_odds(old_pair);
            if (score < -1e50) continue;
            if (local) score+=std::log(double(neighbors[old_pair].size())/neighbors[new_pair].size());
            double old_value=state[cross_start+old_pair], new_value=old_value;
            if (family==2) new_value+=0.5*(state[1+pair_edges[2*old_pair]]+state[1+pair_edges[2*old_pair+1]]
                -state[1+pair_edges[2*new_pair]]-state[1+pair_edges[2*new_pair+1]]);
            std::fill(changes.begin(),changes.end(),0.0);
            for (int row:pair_rows[old_pair]) changes[row]-=old_value;
            for (int row:pair_rows[new_pair]) changes[row]+=new_value;
            for (int row=0; row<observations; ++row) if (changes[row]!=0)
                score+=log_likelihood(row,rate[row]+changes[row],latent[row])-likelihood[row];
            if (accept(score)) {
                included[position]=new_pair;
                state[cross_start+old_pair]=0;
                state[cross_start+new_pair]=new_value;
                for (int row=0; row<observations; ++row) if (changes[row]!=0) {
                    rate[row]+=changes[row];
                    likelihood[row]=log_likelihood(row,rate[row],latent[row]);
                }
            }
        }
    }

    double drift(int row) {
        if (family != 3) return 0.0;
        return state[drift_start] * std::sin(6.283185307179586 * state[drift_start+1] * context[row]
               + state[drift_start+2]) + state[drift_start+3] * (context[row]-0.5);
    }

    double log_likelihood(int row, double new_rate, double new_latent) {
        double contrast = 0.58 + 0.37 / (1.0 + std::exp(-new_latent));
        double probability = contrast * std::exp(-depth[row] * new_rate);
        probability = floor + (1.0-floor) * probability;
        return temperature*(successes[row] * std::log(probability) + (shots[row]-successes[row]) * std::log1p(-probability));
    }

    void refresh() {
        for (int row=0; row<observations; ++row) {
            rate[row] = state[0];
            latent[row] = state[spam_start] + state[spam_start+1] * size[row] + drift(row);
            double normalization = std::sqrt(std::max(1.0, size[row] * (edges == 24 ? 8 : edges == 31 ? 10 : 12)));
            for (int edge=0; edge<edges; ++edge) if (design[row*edges+edge]) {
                rate[row] += state[1+edge];
                latent[row] += state[spam_start+2+edge] / normalization;
            }
            for (int pair=0; pair<pairs; ++pair)
                if (design[row*edges+pair_edges[2*pair]] && design[row*edges+pair_edges[2*pair+1]])
                    rate[row] += state[cross_start+pair];
            likelihood[row] = log_likelihood(row, rate[row], latent[row]);
        }
    }

    void sample_anchor() {
        if (anchors <= 1) return;
        double largest=-1e300;
        for (int candidate=0; candidate<anchors; ++candidate) {
            double score=0;
            for (int pair=0; pair<pairs; ++pair) if (state[cross_start+pair] > 0)
                score += odds[candidate*pairs+pair];
            anchor_score[candidate]=score;
            largest=std::max(largest,score);
        }
        double total=0;
        for (double &score:anchor_score) { score=std::exp(score-largest); total+=score; }
        double threshold=uniform()*total;
        anchor=anchors-1;
        for (int candidate=0; candidate<anchors; ++candidate) {
            threshold-=anchor_score[candidate];
            if (threshold <= 0) { anchor=candidate; break; }
        }
    }

    void cross_update(int pair) {
        double old_value=state[cross_start+pair];
        int without=active-(old_value>0);
        double values[8], scores[8];
        values[0]=0;
        double lower=0.010, width=0.025;
        if (family==2) {
            lower=0.020-0.5*(state[1+pair_edges[2*pair]]+state[1+pair_edges[2*pair+1]]);
            width=0.015;
        }
        double largest=-1e300;
        for (int choice=0; choice<8; ++choice) {
            if (choice) values[choice]=lower+width*nodes[choice-1];
            if ((!choice && without<minimum) || (choice && without>=maximum)) {
                scores[choice]=-1e300;
                continue;
            }
            double score=choice ? prior_odds(pair)+std::log(weights[choice-1]) : 0;
            double difference=values[choice]-old_value;
            for (int row:pair_rows[pair])
                score += log_likelihood(row, rate[row]+difference, latent[row])-likelihood[row];
            scores[choice]=score;
            largest=std::max(largest,score);
        }
        double total=0;
        for (double &score:scores) { score=std::exp(score-largest); total+=score; }
        double threshold=uniform()*total;
        int chosen=7;
        for (int choice=0; choice<8; ++choice) {
            threshold-=scores[choice];
            if (threshold<=0) { chosen=choice; break; }
        }
        double difference=values[chosen]-old_value;
        state[cross_start+pair]=values[chosen];
        active=without+(chosen>0);
        if (difference != 0) for (int row:pair_rows[pair]) {
            rate[row]+=difference;
            likelihood[row]=log_likelihood(row,rate[row],latent[row]);
        }
    }

    void continuous_update(int parameter, double proposal, const std::vector<int>& rows, bool spam, int mode) {
        double difference=proposal-state[parameter];
        double score=0;
        for (int row:rows) {
            double change=difference;
            if (mode==1) change*=size[row];
            if (mode==2) change/=std::sqrt(std::max(1.0,size[row]*(edges==24?8:edges==31?10:12)));
            score += log_likelihood(row,rate[row]+(spam?0:change),latent[row]+(spam?change:0))-likelihood[row];
        }
        if (accept(score)) {
            state[parameter]=proposal;
            for (int row:rows) {
                double change=difference;
                if (mode==1) change*=size[row];
                if (mode==2) change/=std::sqrt(std::max(1.0,size[row]*(edges==24?8:edges==31?10:12)));
                if (spam) latent[row]+=change; else rate[row]+=change;
                likelihood[row]=log_likelihood(row,rate[row],latent[row]);
            }
        }
    }

    void drift_update(int parameter) {
        double lower[4]={0.4,0.5,0.0,-0.8}, width[4]={0.5,1.0,6.283185307179586,1.6};
        double old_value=state[drift_start+parameter];
        std::vector<double> old_drift(observations);
        for (int row=0; row<observations; ++row) old_drift[row]=drift(row);
        state[drift_start+parameter]=lower[parameter]+width[parameter]*uniform();
        double score=0;
        for (int row=0; row<observations; ++row)
            score+=log_likelihood(row,rate[row],latent[row]+drift(row)-old_drift[row])-likelihood[row];
        if (accept(score)) {
            for (int row=0; row<observations; ++row) {
                latent[row]+=drift(row)-old_drift[row];
                likelihood[row]=log_likelihood(row,rate[row],latent[row]);
            }
        } else state[drift_start+parameter]=old_value;
    }
};

extern "C" void sample_posterior(int edges, int pairs, int observations, int family, int anchors,
    const int *pair_edges, const double *odds, const double *design, const double *depth,
    const double *successes, const double *shots, const double *context,
    double *state, double *output, int samples, int burn, int thin, uint64_t seed
#ifdef TEMPERED
    , double temperature
#endif
    ) {
    Sampler sampler;
    sampler.edges=edges; sampler.pairs=pairs; sampler.observations=observations;
    sampler.family=family; sampler.anchors=anchors; sampler.pair_edges=pair_edges;
    sampler.odds=odds; sampler.design=design; sampler.depth=depth; sampler.successes=successes;
    sampler.shots=shots; sampler.context=context; sampler.state=state;
#ifdef TEMPERED
    sampler.temperature=temperature;
#else
    sampler.temperature=1.0;
#endif
    sampler.minimum=int(std::round(0.30*edges))-1; sampler.maximum=sampler.minimum+3;
    sampler.cross_start=1+edges; sampler.spam_start=1+edges+pairs;
    sampler.drift_start=sampler.spam_start+2+edges; sampler.dimension=sampler.drift_start+4;
    sampler.floor=std::pow(2.0,-(edges==24?16:edges==31?20:25));
    sampler.random.seed(seed); sampler.anchor=0; sampler.active=0;
    sampler.edge_rows.resize(edges); sampler.pair_rows.resize(pairs);
    sampler.rate.resize(observations); sampler.latent.resize(observations);
    sampler.likelihood.resize(observations); sampler.size.resize(observations);
    sampler.anchor_score.resize(anchors);
    sampler.neighbors.resize(pairs);
    sampler.pair_weight_sum=0;
    for (int pair=0; pair<pairs; ++pair) {
        double separation=0.022-state[1+pair_edges[2*pair]]-state[1+pair_edges[2*pair+1]];
        sampler.pair_weight_sum+=separation*separation;
        for (int other=0; other<pairs; ++other)
            if (pair!=other && (pair_edges[2*pair]==pair_edges[2*other] || pair_edges[2*pair]==pair_edges[2*other+1]
                || pair_edges[2*pair+1]==pair_edges[2*other] || pair_edges[2*pair+1]==pair_edges[2*other+1]))
                sampler.neighbors[pair].push_back(other);
    }
    for (int pair=0; pair<pairs; ++pair) sampler.active+=(state[1+edges+pair]>0);
    for (int row=0; row<observations; ++row) {
        double count=0;
        for (int edge=0; edge<edges; ++edge) if (design[row*edges+edge]) {
            sampler.edge_rows[edge].push_back(row); count+=1;
        }
        sampler.size[row]=count/(edges==24?8:edges==31?10:12);
        for (int pair=0; pair<pairs; ++pair)
            if (design[row*edges+pair_edges[2*pair]] && design[row*edges+pair_edges[2*pair+1]])
                sampler.pair_rows[pair].push_back(row);
    }
    sampler.refresh();
    std::vector<int> all_rows(observations), order(pairs);
    std::iota(all_rows.begin(),all_rows.end(),0); std::iota(order.begin(),order.end(),0);
    int saved=0;
    for (int sweep=0; sweep<burn+samples*thin; ++sweep) {
        if (sweep%4==0) sampler.sample_anchor();
        sampler.continuous_update(0,0.001+0.003*sampler.uniform(),all_rows,false,0);
        for (int edge=0; edge<edges; ++edge) {
            double proposal=family>=2 ? std::exp(std::log(0.0015)+std::log(0.010/0.0015)*sampler.uniform())
                                     : 0.002+0.005*sampler.uniform();
#ifdef IMPROVED_PRIOR
            if (family==2) sampler.anticorrelated_base(edge,proposal);
            else sampler.continuous_update(1+edge,proposal,sampler.edge_rows[edge],false,0);
#else
            sampler.continuous_update(1+edge,proposal,sampler.edge_rows[edge],false,0);
#endif
        }
        std::shuffle(order.begin(),order.end(),sampler.random);
        for (int pair:order) sampler.cross_update(pair);
#ifdef IMPROVED_PRIOR
        sampler.swap_updates();
#endif
        sampler.continuous_update(sampler.spam_start,-0.4+0.8*sampler.uniform(),all_rows,true,0);
        sampler.continuous_update(sampler.spam_start+1,-1+2*sampler.uniform(),all_rows,true,1);
        for (int edge=0; edge<edges; ++edge)
            sampler.continuous_update(sampler.spam_start+2+edge,-0.9+1.8*sampler.uniform(),sampler.edge_rows[edge],true,2);
        if (family==3) for (int parameter=0; parameter<4; ++parameter) sampler.drift_update(parameter);
        if (sweep>=burn && (sweep-burn)%thin==0) {
            std::copy(state,state+sampler.dimension,output+saved*sampler.dimension);
            ++saved;
        }
    }
}
