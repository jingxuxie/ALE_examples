#include <alps/alea/batch.hpp>
#include <alps/alea/transform.hpp>
#include <boost/property_tree/json_parser.hpp>
#include <boost/property_tree/ptree.hpp>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <string>
#include <vector>

using Tree = boost::property_tree::ptree;
using Column = alps::alea::column<double>;
using Matrix = Eigen::MatrixXd;

double evaluate(const Tree &expression, const Column &means) {
    auto moment = expression.get_optional<std::size_t>("moment");
    if (moment) return means(*moment + 1) / means(0);
    auto constant = expression.get_optional<double>("constant");
    if (constant) return *constant;
    const std::string operation = expression.get<std::string>("op");
    std::vector<double> arguments;
    for (const auto &argument : expression.get_child("args"))
        arguments.push_back(evaluate(argument.second, means));
    if (operation == "add") return arguments.at(0) + arguments.at(1);
    if (operation == "sub") return arguments.at(0) - arguments.at(1);
    if (operation == "mul") return arguments.at(0) * arguments.at(1);
    if (operation == "div") return arguments.at(0) / arguments.at(1);
    if (operation == "log") return std::log(arguments.at(0));
    if (operation == "sqrt") return std::sqrt(arguments.at(0));
    throw std::runtime_error("unsupported expression operation");
}

class ObservableTransform : public alps::alea::transformer<double> {
public:
    ObservableTransform(std::size_t dimension, const std::vector<Tree> &expressions)
        : dimension_(dimension), expressions_(expressions) {}
    std::size_t in_size() const override { return dimension_; }
    std::size_t out_size() const override { return expressions_.size(); }
    bool is_linear() const override { return false; }
    Column operator()(const Column &means) const override {
        Column result(expressions_.size());
        for (std::size_t index = 0; index < expressions_.size(); ++index)
            result(index) = evaluate(expressions_[index], means);
        return result;
    }
private:
    std::size_t dimension_;
    std::vector<Tree> expressions_;
};

alps::alea::batch_data<double> concatenate(
        const std::vector<alps::alea::batch_data<double>> &replicas) {
    std::size_t nonempty = 0;
    for (const auto &replica : replicas)
        for (Eigen::Index index = 0; index < replica.count().size(); ++index)
            if (replica.count()(index)) ++nonempty;
    alps::alea::batch_data<double> result(replicas.at(0).size(), nonempty);
    std::size_t destination = 0;
    for (const auto &replica : replicas) {
        for (Eigen::Index index = 0; index < replica.count().size(); ++index) {
            if (!replica.count()(index)) continue;
            result.batch().col(destination) = replica.batch().col(index);
            result.count()(destination) = replica.count()(index);
            ++destination;
        }
    }
    return result;
}

void write_vector(std::ostream &output, const Column &values) {
    output << '[';
    for (Eigen::Index index = 0; index < values.size(); ++index) {
        if (index) output << ',';
        output << values(index);
    }
    output << ']';
}

void write_statistics(std::ostream &output,
        const alps::alea::batch_data<double> &batches,
        const ObservableTransform &transform) {
    alps::alea::batch_result<double> input(batches);
    auto result = alps::alea::transform(alps::alea::jackknife_prop(), transform, input);
    Matrix covariance = result.cov() / result.observations();
    output << "{\"mean\":";
    write_vector(output, result.mean());
    output << ",\"covariance\":[";
    for (Eigen::Index row = 0; row < covariance.rows(); ++row) {
        if (row) output << ',';
        output << '[';
        for (Eigen::Index column = 0; column < covariance.cols(); ++column) {
            if (column) output << ',';
            output << covariance(row, column);
        }
        output << ']';
    }
    output << "]}";
}

int main(int argc, char **argv) {
    try {
        std::string input_path, output_path;
        for (int index = 1; index + 1 < argc; index += 2) {
            const std::string option(argv[index]);
            if (option == "--input") input_path = argv[index + 1];
            else if (option == "--output") output_path = argv[index + 1];
            else throw std::runtime_error("unknown argument");
        }
        if (input_path.empty() || output_path.empty())
            throw std::runtime_error("--input and --output are required");
        Tree input;
        boost::property_tree::read_json(input_path, input);
        std::vector<Tree> expressions;
        for (const auto &expression : input.get_child("expressions"))
            expressions.push_back(expression.second);
        std::vector<std::vector<Column>> streams;
        std::size_t dimension = 0;
        for (const auto &replica : input.get_child("replicas")) {
            std::vector<Column> stream;
            auto sign_iterator = replica.second.get_child("signs").begin();
            for (const auto &row : replica.second.get_child("measurements")) {
                dimension = row.second.size() + 1;
                Column measured(dimension);
                const double sign = sign_iterator->second.get_value<double>();
                measured(0) = sign;
                std::size_t column = 1;
                for (const auto &entry : row.second)
                    measured(column++) = sign * entry.second.get_value<double>();
                stream.push_back(measured);
                ++sign_iterator;
            }
            streams.push_back(stream);
        }
        ObservableTransform transform(dimension, expressions);
        std::ofstream output(output_path);
        if (!output) throw std::runtime_error("cannot open output");
        output << std::setprecision(17) << "{\"schema_version\":1,\"analyses\":[";
        bool first = true;
        for (const auto &block : input.get_child("block_sizes")) {
            const std::size_t block_size = block.second.get_value<std::size_t>();
            std::vector<alps::alea::batch_data<double>> replicas;
            for (const auto &stream : streams) {
                std::size_t slots = 2;
                while (slots < (stream.size() + block_size - 1) / block_size)
                    slots *= 2;
                alps::alea::batch_acc<double> accumulator(dimension, slots, block_size);
                for (const auto &measurement : stream) accumulator << measurement;
                auto result = accumulator.finalize();
                replicas.push_back(concatenate({result.store()}));
            }
            if (!first) output << ',';
            first = false;
            output << "{\"block_size\":" << block_size << ",\"pooled\":";
            write_statistics(output, concatenate(replicas), transform);
            output << ",\"replicas\":[";
            for (std::size_t index = 0; index < replicas.size(); ++index) {
                if (index) output << ',';
                write_statistics(output, replicas[index], transform);
            }
            output << "]}";
        }
        output << "]}\n";
        return 0;
    } catch (const std::exception &error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
