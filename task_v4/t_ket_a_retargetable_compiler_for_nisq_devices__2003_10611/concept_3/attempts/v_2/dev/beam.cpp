#define OPTIMIZE_LIBRARY
#include "optimize.cpp"
#include <unordered_map>

struct BeamState {
    End front, back;
    uint64_t remaining;
    double score;
};

uint64_t signature(const BeamState& state) {
    uint64_t result = state.remaining;
    for (Mask mask : state.front.rows) result = (result ^ mask) * 0x9e3779b97f4a7c15ull;
    for (Mask mask : state.back.rows) result = (result ^ mask) * 0x9e3779b97f4a7c15ull;
    return result;
}

struct BeamWeights {
    double matrix, parity, clock, count, native;
};
int beam_mode = 0;

double evaluate(const Case& instance, const BeamState& state, BeamWeights parameters) {
    double result = parameters.count * (state.front.gates.size()+state.back.gates.size());
    int maximum = 0, total_clock = 0;
    for (int wire = 0; wire < instance.size; ++wire) {
        maximum = max(maximum,state.front.clocks[wire]+state.back.clocks[wire]);
        total_clock += state.front.clocks[wire]+state.back.clocks[wire];
    }
    result += parameters.clock * (maximum + 0.04*total_clock);
    Matrix residual = multiply(state.back.rows,state.front.inverse_rows);
    Matrix reverse = multiply(state.front.rows,state.back.inverse_rows);
    for (int wire = 0; wire < instance.size; ++wire) {
        auto metric = [&](Mask mask) {
            return (1-parameters.native) * (weight(mask)-1) + parameters.native * (2*instance.steiner[mask | (1u << wire)]-weight(mask)+1);
        };
        result += parameters.matrix * (metric(residual[wire])+metric(reverse[wire]));
    }
    for (int index = 0; index < instance.parity_count; ++index) if (state.remaining >> index & 1) {
        Mask front_mask = transform(instance.parities[index],state.front.inverse_rows);
        Mask back_mask = transform(instance.parities[index],state.back.inverse_rows);
        int front_cost = 2*instance.steiner[front_mask]-weight(front_mask)+1;
        int back_cost = 2*instance.steiner[back_mask]-weight(back_mask)+1;
        result += parameters.parity * min(front_cost,back_cost);
    }
    return result;
}

Circuit beam_solve(const Case& instance, int width, int variant) {
    BeamWeights parameters{0.3,0.5,2,1,0.4};
    if (variant) parameters = {0.1+uniform()*0.5, 0.2+uniform(), 0.5+uniform()*4, 0.2+uniform(), uniform()*0.8};
    if (beam_mode && (beam_mode < 3 || variant%2)) parameters.matrix = 0.4 + uniform()*2.5;
    BeamState initial{{identity(instance.size),identity(instance.size),{},vector<int>(instance.size)},
                      {instance.target,inverse(instance.target),{},vector<int>(instance.size)},
                      (1ull << instance.parity_count)-1,0};
    for (int index = 0; index < instance.parity_count; ++index) {
        Mask parity = instance.parities[index];
        if (weight(parity) == 1 || find(instance.target.begin(),instance.target.end(),parity) != instance.target.end()) initial.remaining &= ~(1ull << index);
    }
    vector<BeamState> beam{initial};
    Circuit best_result;
    double best_result_score = 1e9;
    for (int step = 0; step < instance.parity_count*(beam_mode == 7 ? 3 : 1) && !beam.empty(); ++step) {
        vector<BeamState> candidates;
        for (const BeamState& base : beam) {
            vector<BeamState> parents{base};
            if (beam_mode == 5 || beam_mode == 6) {
                Circuit bridge = finish_matrix(instance,multiply(base.back.rows,base.front.inverse_rows),uniform());
                for (int side = 0; side < 2; ++side) {
                    BeamState advanced = base;
                    End& endpoint = side ? advanced.back : advanced.front;
                    int advance = min(int(bridge.size()),1+int(rng()%6));
                    for (int index = 0; index < advance; ++index) {
                        Gate gate = side ? bridge[bridge.size()-1-index] : bridge[index];
                        append(endpoint,{gate});
                        Mask new_mask = endpoint.rows[gate.second];
                        for (int parity = 0; parity < instance.parity_count; ++parity) if (instance.parities[parity] == new_mask) advanced.remaining &= ~(1ull << parity);
                    }
                    parents.push_back(std::move(advanced));
                }
            }
            for (const BeamState& parent : parents) {
            if (!parent.remaining) { candidates.push_back(parent); continue; }
            struct Option { int side, parity, root, cost; };
            vector<Option> options;
            int minimum_cost = 100;
            for (int side = 0; side < 2; ++side) {
                const End& endpoint = side ? parent.back : parent.front;
                for (int index = 0; index < instance.parity_count; ++index) if (parent.remaining >> index & 1) {
                    Mask mask = transform(instance.parities[index],endpoint.inverse_rows);
                    for (int root = 0; root < instance.size; ++root) if (mask >> root & 1) {
                        int cost = 2*instance.steiner[mask]-weight(mask)+1;
                        minimum_cost = min(minimum_cost,cost);
                        options.push_back({side,index,root,cost});
                    }
                }
            }
            if (beam_mode == 7 && step%3 != 2) {
                for (int side = 0; side < 2; ++side) {
                    const End& endpoint = side ? parent.back : parent.front;
                    const End& other = side ? parent.front : parent.back;
                    for (int index = 0; index < instance.size; ++index) {
                        Mask mask = transform(other.rows[index],endpoint.inverse_rows);
                        if (weight(mask) <= 1) continue;
                        int cost = 2*instance.steiner[mask]-weight(mask)+1;
                        if (cost > minimum_cost+2) continue;
                        for (int root = 0; root < instance.size; ++root) if (mask >> root & 1) options.push_back({side,-index-1,root,cost});
                    }
                }
            }
            vector<BeamState> children;
            for (Option option : options) if (option.cost <= minimum_cost+1+(variant%3 == 2)+(beam_mode ? variant%3 : 0)) {
                BeamState child = parent;
                End& endpoint = option.side ? child.back : child.front;
                Mask desired = option.parity >= 0 ? instance.parities[option.parity] : (option.side ? child.front : child.back).rows[-option.parity-1];
                Mask mask = transform(desired,endpoint.inverse_rows);
                Tree tree = make_tree(instance,mask,option.root,(1u << instance.size)-1,variant ? 0.5 : 0);
                Circuit gates = reduce_vector(tree,mask);
                for (Gate& gate : gates) swap(gate.first,gate.second);
                for (Gate gate : gates) {
                    append(endpoint,{gate});
                    Mask new_mask = endpoint.rows[gate.second];
                    for (int index = 0; index < instance.parity_count; ++index) if (instance.parities[index] == new_mask) child.remaining &= ~(1ull << index);
                }
                child.score = evaluate(instance,child,parameters);
                children.push_back(std::move(child));
            }
            sort(children.begin(),children.end(),[](const BeamState& first,const BeamState& second) { return first.score < second.score; });
            int branch_limit = max(8,width/4);
            for (int index = 0; index < min(branch_limit,int(children.size())); ++index) candidates.push_back(std::move(children[index]));
            }
        }
        sort(candidates.begin(),candidates.end(),[](const BeamState& first,const BeamState& second) { return first.score < second.score; });
        if (beam_mode == 2) {
            if (int(candidates.size()) > width*4) candidates.resize(width*4);
            double parity_factor = 0.2 + 0.8*uniform();
            for (BeamState& candidate : candidates) {
                Circuit bridge = finish_matrix(instance,multiply(candidate.back.rows,candidate.front.inverse_rows),0);
                Circuit complete = candidate.front.gates;
                complete.insert(complete.end(),bridge.begin(),bridge.end());
                complete.insert(complete.end(),candidate.back.gates.rbegin(),candidate.back.gates.rend());
                BeamWeights parity_parameters{0,parity_factor,0,0,0};
                candidate.score = depth(complete,instance.size)+complete.size()*0.04+evaluate(instance,candidate,parity_parameters);
            }
            sort(candidates.begin(),candidates.end(),[](const BeamState& first,const BeamState& second) { return first.score < second.score; });
        }
        beam.clear();
        unordered_set<uint64_t> used;
        unordered_map<uint64_t,int> clusters;
        int completed = 0;
        for (BeamState& candidate : candidates) {
            if (!candidate.remaining) {
                if (++completed > width) continue;
                for (int trial = 0; trial < 4; ++trial) {
                    Circuit bridge = finish_matrix(instance,multiply(candidate.back.rows,candidate.front.inverse_rows),trial ? uniform() : 0);
                    Circuit result = candidate.front.gates;
                    result.insert(result.end(),bridge.begin(),bridge.end());
                    result.insert(result.end(),candidate.back.gates.rbegin(),candidate.back.gates.rend());
                    result = stripped(cancel(schedule(cancel(annotated(instance,result,0)),0)));
                    double score = depth(result,instance.size) + result.size()*0.04;
                    if (score < best_result_score) { best_result_score = score; best_result = result; }
                }
                continue;
            }
            uint64_t key = signature(candidate);
            if (int(beam.size()) < width && (!beam_mode || clusters[candidate.remaining] < max(8,width/12)) && used.insert(key).second) {
                ++clusters[candidate.remaining];
                beam.push_back(std::move(candidate));
            }
        }
    }
    return best_result;
}

int main(int argc, char** argv) {
    int selected = argc > 1 ? stoi(argv[1]) : 0;
    int seconds = argc > 2 ? stoi(argv[2]) : 60;
    int width = argc > 3 ? stoi(argv[3]) : 100;
    if (argc > 4) rng.seed(stoull(argv[4]));
    if (argc > 5) beam_mode = stoi(argv[5]);
    Case instance = read_cases()[selected];
    prepare_steiner(instance);
    Circuit best = read_gates("dev/"+instance.id+".beam");
    double best_score = best.empty() ? 1e9 : depth(best,instance.size)+best.size()*0.04;
    auto started = chrono::steady_clock::now();
    vector<pair<int,Mask>> hints;
    if (beam_mode == 3 || beam_mode == 4 || beam_mode == 6) {
        set<Mask> known(instance.parities.begin(),instance.parities.end());
        for (Mask mask : instance.target) known.insert(mask);
        for (Mask mask : identity(instance.size)) known.insert(mask);
        vector<Mask> masks(known.begin(),known.end());
        unordered_map<Mask,int> frequencies;
        for (int first = 0; first < int(masks.size()); ++first) for (int second = first+1; second < int(masks.size()); ++second) ++frequencies[masks[first]^masks[second]];
        for (auto [mask,frequency] : frequencies) if (frequency >= 2 && !known.count(mask)) hints.emplace_back(frequency,mask);
        sort(hints.rbegin(),hints.rend());
    }
    for (int iteration = 0; chrono::duration<double>(chrono::steady_clock::now()-started).count() < seconds; ++iteration) {
        Case augmented = instance;
        if (beam_mode == 3 || beam_mode == 4 || beam_mode == 6) {
            int limit = beam_mode == 3 ? 8 : 16;
            vector<pair<double,pair<int,Mask>>> ordered_hints;
            Matrix inverse_target = inverse(instance.target);
            for (auto [frequency,mask] : hints) {
                Mask reverse_mask = transform(mask,inverse_target);
                double cost = min(2*instance.steiner[mask]-weight(mask)+1,2*instance.steiner[reverse_mask]-weight(reverse_mask)+1);
                ordered_hints.push_back({frequency+uniform()*0.9-cost*0.04,{frequency,mask}});
            }
            sort(ordered_hints.rbegin(),ordered_hints.rend());
            for (auto [priority,hint] : ordered_hints) {
                auto [frequency,mask] = hint;
                if (int(augmented.parities.size()) >= min(60,instance.parity_count+limit)) break;
                if (frequency >= 3 || (beam_mode >= 4 && uniform() < 0.15)) augmented.parities.push_back(mask);
            }
            augmented.parity_count = augmented.parities.size();
        }
        Circuit result = beam_solve(augmented,width,iteration);
        if (!valid(instance,result)) throw runtime_error("invalid beam result");
        if (beam_mode >= 3) result = stripped(cancel(schedule(cancel(annotated(instance,result,0)),0)));
        double score = depth(result,instance.size)+result.size()*0.04;
        if (score < best_score+12) {
            string seed_name = argc > 4 ? argv[4] : "default";
            save_gates("dev/candidates/"+instance.id+"_"+seed_name+"_"+to_string(beam_mode)+"_"+to_string(iteration)+".gates",result);
        }
        if (score < best_score) {
            best_score = score;
            best = result;
            Circuit saved = read_gates("dev/"+instance.id+".beam");
            if (saved.empty() || score < depth(saved,instance.size)+saved.size()*0.04) save_gates("dev/"+instance.id+".beam",best);
            cerr << instance.id << " beam " << iteration << " count=" << best.size() << " depth=" << depth(best,instance.size) << endl;
        }
    }
}
