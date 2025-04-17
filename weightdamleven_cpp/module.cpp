#include <Windows.h>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <iostream>
#include <tuple>
#include <thread>
#include <mutex>
#include <algorithm>

namespace py = pybind11;

class WeightDamLeven
{

private:
    std::vector<std::vector<int>> m_keys_encoded;
    std::vector<std::vector<double>> m_cost_matrix;
    bool m_is_key_cost;
    double m_replace_cost;
    double m_insert_cost;
    double m_append_cost;
    double m_delete_cost;
    double m_transpose_cost;

public:
    WeightDamLeven(
        std::vector<std::vector<int>>& keys_encoded,
        std::vector<std::vector<double>>& cost_matrix,
        bool is_key_cost,
        double replace_cost, /* if is_key_cost, then this value is used when a key is out of cost_matrix */
        double insert_cost,
        double append_cost,
        double delete_cost,
        double transpose_cost)
    {
        m_keys_encoded = keys_encoded;
        m_cost_matrix = cost_matrix;
        m_is_key_cost = is_key_cost;
        m_replace_cost = replace_cost;
        m_insert_cost = insert_cost;
        m_append_cost = append_cost;
        m_delete_cost = delete_cost;
        m_transpose_cost = transpose_cost;
    }

    double key_weighted_damerau_levenshtein(
        const std::vector<int>& str1,
        const std::vector<int>& str2,
        const double score_to_beat)
    {
        size_t len1 = str1.size();
        size_t len2 = str2.size();
        std::vector<std::vector<double>> matrix(len1 + 1);
        for (int i = 0; i < len1 + 1; ++i)
        {
            matrix[i] = std::vector<double>(len2 + 1, 0.0);
        }
        for (int i = 1; i < len1 + 1; ++i)
        {
            matrix[i][0] = i * m_delete_cost;
        }
        for (int j = 1; j < len2 + 1; ++j)
        {
            double insert_append_cost = j > len1 ? m_append_cost : m_insert_cost;
            matrix[0][j] = matrix[0][j-1] + insert_append_cost;
        }
        for (int i = 1; i < len1 + 1; ++i)
        {
            double best_score_this_row = matrix[i][0];
            for (int j = 1; j < len2 + 1; ++j)
            {
                double replace_cost_curr = 0.0;
                int str1_idx = str1[i - 1];
                int str2_idx = str2[j - 1];
                if (str1_idx == str2_idx)
                {
                    replace_cost_curr = 0.0;
                }
                else if (m_is_key_cost)
                {
                    replace_cost_curr = m_replace_cost;
                    if (str1_idx < m_cost_matrix.size() && str2_idx < m_cost_matrix.size())
                    {
                        replace_cost_curr = m_cost_matrix[str1_idx][str2_idx];
                    }
                }
                else
                {
                    replace_cost_curr = m_replace_cost;
                }

                double insert_append_cost = j > len1 ? m_append_cost : m_insert_cost;
                matrix[i][j] = min(
                    matrix[i - 1][j] + m_delete_cost, // delete
                    matrix[i][j - 1] + insert_append_cost); // insert
                matrix[i][j] = min(
                    matrix[i][j],
                    matrix[i - 1][j - 1] + replace_cost_curr); // replace
                if (i > 1 && j > 1 && str1_idx == str2[j - 2] && str1[i - 2] == str2_idx)
                {
                    matrix[i][j] = min(
                        matrix[i][j],
                        matrix[i - 2][j - 2] + m_transpose_cost); // transpose
                }

                best_score_this_row = min(best_score_this_row, matrix[i][j]);
            }
            if (score_to_beat >= 0 && best_score_this_row >= score_to_beat)
            {
                return score_to_beat + 1.0;
            }
        }
        return matrix.back().back();
    }

    std::vector<std::vector<int>> weighted_damerau_levenshtein(
        std::vector<int>& target_word_int,
        int num_results)
    {
        num_results = max(num_results, 1);
        std::vector<std::tuple<std::vector<int>, double>> word_scores;
        word_scores.reserve(m_keys_encoded.size());
        num_results = min(num_results, (int)(m_keys_encoded.size()));
        double score_to_beat = -1.0;

        for (int counter = 0; counter < m_keys_encoded.size(); ++counter)
        {
            std::vector<int>& word = m_keys_encoded[counter];

            // Inserting elements in sorted order
            double score = key_weighted_damerau_levenshtein(
                target_word_int,
                word,
                score_to_beat);
            if (score_to_beat >= 0 && score >= score_to_beat)
            {
                continue;
            }
            std::tuple<std::vector<int>, double> new_word_score(word, score);
            auto it = upper_bound(word_scores.begin(), word_scores.end(), new_word_score,
                [](const auto& a, const auto& b) { return std::get<1>(a) < std::get<1>(b); });
            word_scores.insert(it, new_word_score);
            if (counter == num_results - 1)
            {
                score_to_beat = std::get<1>(word_scores[num_results - 1]);
            }
            else if (counter >= num_results)
            {
                score_to_beat = min(score_to_beat, std::get<1>(word_scores[num_results - 1]));
            }
        }
        
        std::vector<std::vector<int>> words(num_results);
        for (int i = 0; i < num_results; ++i)
        {
            words[i] = std::get<0>(word_scores[i]);
        }
        return words;
    }

    std::vector<std::vector<int>> weighted_damerau_levenshtein_multithread(
        std::vector<int>& target_word_int,
        int num_results)
    {
        num_results = max(num_results, 1);
        int thread_count = (int)std::thread::hardware_concurrency();
        std::vector<std::tuple<std::vector<int>, double>> word_scores;
        word_scores.reserve(m_keys_encoded.size());
        num_results = min(num_results, (int)(m_keys_encoded.size()));
        double score_to_beat = -1.0;

        std::mutex word_scores_mutex;
        auto score_loop = [
            this,
            &num_results,
            &target_word_int,
            &word_scores_mutex,
            &word_scores,
            &score_to_beat](
            int counter_start,
            int counter_stop)
        {
            for (int counter = counter_start; counter < counter_stop; ++counter)
            {
                std::vector<int>& word = m_keys_encoded[counter];

                // Inserting elements in sorted order
                double score = key_weighted_damerau_levenshtein(
                    target_word_int,
                    word,
                    score_to_beat);
                if (score_to_beat >= 0 && score >= score_to_beat)
                {
                    continue;
                }

                std::lock_guard<std::mutex> lock(word_scores_mutex); // Acquire mutex
                std::tuple<std::vector<int>, double> new_word_score(word, score);
                auto it = upper_bound(word_scores.begin(), word_scores.end(), new_word_score,
                    [](const auto& a, const auto& b) { return std::get<1>(a) < std::get<1>(b); });
                word_scores.insert(it, new_word_score);
                if (word_scores.size() == num_results)
                {
                    score_to_beat = std::get<1>(word_scores[num_results - 1]);
                }
                else if (word_scores.size() > num_results)
                {
                    score_to_beat = min(score_to_beat, std::get<1>(word_scores[num_results - 1]));
                }
            }
        };

        int chunk_size = (int)std::ceil(m_keys_encoded.size() / (double)thread_count);
        int counter_start = 0;
        int counter_stop = 0;
        std::vector<std::thread> threads(thread_count);
        for (int i = 0; i < thread_count; ++i)
        {
            counter_stop = min(counter_start + chunk_size, (int)m_keys_encoded.size());
            threads[i] = std::thread(
                score_loop,
                counter_start,
                counter_stop);
            counter_start = counter_stop;
        }
        for (int i = 0; i < thread_count; ++i)
        {
            threads[i].join();
        }

        std::vector<std::vector<int>> words(num_results);
        for (int i = 0; i < num_results; ++i)
        {
            words[i] = std::get<0>(word_scores[i]);
        }
        return words;
    }

    std::vector<int> weighted_damerau_levenshtein_single(
        std::vector<int>& target_word_int)
    {
        std::vector<std::vector<int>> words = weighted_damerau_levenshtein(
            target_word_int, 1);
        return words[0];
    }

    std::vector<int> weighted_damerau_levenshtein_single_multithread(
        std::vector<int>& target_word_int)
    {
        std::vector<std::vector<int>> words = weighted_damerau_levenshtein_multithread(
            target_word_int, 1);
        return words[0];
    }
};

PYBIND11_MODULE(weightdamleven, m)
{
    py::class_<WeightDamLeven>(m, "WeightDamLeven")
        .def(py::init<
                std::vector<std::vector<int>>&,
                std::vector<std::vector<double>>&,
                bool,
                double,
                double,
                double,
                double,
                double>(),
            "Constructor.",
            py::arg("keys_encoded"),
            py::arg("cost_matrix"),
            py::arg("is_key_cost"),
            py::arg("replace_cost"),
            py::arg("insert_cost"),
            py::arg("append_cost"),
            py::arg("delete_cost"),
            py::arg("transpose_cost"))
        .def("weighted_damerau_levenshtein",
            &WeightDamLeven::weighted_damerau_levenshtein,
            "Normal Search.",
            py::arg("target_word_int"),
            py::arg("num_results"))
        .def("weighted_damerau_levenshtein_multithread",
            &WeightDamLeven::weighted_damerau_levenshtein_multithread,
            "Multithreaded Search.",
            py::arg("target_word_int"),
            py::arg("num_results"))
        .def("weighted_damerau_levenshtein_single",
            &WeightDamLeven::weighted_damerau_levenshtein_single,
            "Find the single best match.",
            py::arg("target_word_int"))
        .def("weighted_damerau_levenshtein_single_multithread",
            &WeightDamLeven::weighted_damerau_levenshtein_single_multithread,
            "Multithreaded single best match.",
            py::arg("target_word_int"))
        .doc() = "WeightDamLeven is used to find close string matches.";
}
