#define LOCAL_LIBRARY
#include "local.cpp"
#include <filesystem>
#include <thread>

int main(int argc, char** argv) {
    int selected = argc > 1 ? stoi(argv[1]) : 4;
    int seconds = argc > 2 ? stoi(argv[2]) : 120;
    double per_candidate = argc > 3 ? stod(argv[3]) : 2;
    Case instance = read_cases()[selected];
    Circuit best;
    double best_score = 1e9;
    for (string extension : {"optimized","local","satlocal","beam","satgates","hot","global","layers","population"}) {
        Circuit candidate = read_gates("dev/"+instance.id+"."+extension);
        if (!candidate.empty() && quality(instance,candidate) < best_score) { best = candidate; best_score = quality(instance,candidate); }
    }
    unordered_set<string> processed;
    auto started = chrono::steady_clock::now();
    while (chrono::duration<double>(chrono::steady_clock::now()-started).count() < seconds) {
        vector<pair<double,string>> files;
        for (const auto& entry : filesystem::directory_iterator("dev/candidates")) {
            string path = entry.path().string();
            if (entry.path().extension() != ".gates" || path.find(instance.id) == string::npos || processed.count(path)) continue;
            Circuit candidate = read_gates(path);
            if (candidate.empty()) continue;
            if (!valid(instance,candidate)) throw runtime_error("invalid population source");
            files.emplace_back(quality(instance,candidate),path);
        }
        sort(files.begin(),files.end());
        if (files.empty()) { this_thread::sleep_for(chrono::milliseconds(200)); continue; }
        for (auto [raw_score,path] : files) {
            processed.insert(path);
            if (raw_score > best_score+25) continue;
            Circuit candidate = read_gates(path);
            Circuit current = annotated(instance,candidate,0);
            double candidate_best = quality(instance,candidate), current_score = candidate_best;
            auto candidate_started = chrono::steady_clock::now();
            int iterations = 0;
            local_mode = 0;
            while (chrono::duration<double>(chrono::steady_clock::now()-candidate_started).count() < per_candidate) {
                Circuit trial = replace_block(instance,current,2000);
                trial = cancel(schedule(cancel(trial),1));
                double score = quality(instance,trial);
                double temperature = 0.4;
                if (score <= current_score || uniform() < exp((current_score-score)/temperature)) { current = trial; current_score = score; }
                if (score < candidate_best) {
                    candidate = stripped(trial);
                    candidate_best = score;
                }
                if (++iterations % 1500 == 0) { current = annotated(instance,candidate,1); current_score = candidate_best; }
            }
            if (!valid(instance,candidate)) throw runtime_error("invalid population optimization");
            save_gates(path+".refined",candidate);
            if (candidate_best < best_score) {
                best = candidate;
                best_score = candidate_best;
                save_gates("dev/"+instance.id+".population",best);
                cerr << instance.id << " population count=" << best.size() << " depth=" << depth(best,instance.size) << " source=" << path << endl;
            }
            if (chrono::duration<double>(chrono::steady_clock::now()-started).count() >= seconds) break;
        }
    }
}
