# -*- coding: utf-8 -*-

IF SPARSELIB == "rsb":
    # librsb requires that rsb.h always be included before "blas_sparse.h"
    cdef extern from "rsb.h":
        pass

cdef extern from "blas_sparse.h":

    enum blas_order_type:
        blas_rowmajor = 101
        blas_colmajor = 102

    enum blas_trans_type:
        blas_no_trans   = 111
        blas_trans      = 112
        blas_conj_trans = 113

    enum blas_uplo_type:
        blas_upper = 121
        blas_lower = 122

    enum blas_diag_type:
        blas_non_unit_diag = 131
        blas_unit_diag     = 132

    enum blas_side_type:
        blas_left_side  = 141
        blas_right_side = 142

    enum blas_cmach_type:
        blas_base      = 151
        blas_t         = 152
        blas_rnd       = 153
        blas_ieee      = 154
        blas_emin      = 155
        blas_emax      = 156
        blas_eps       = 157
        blas_prec      = 158
        blas_underflow = 159
        blas_overflow  = 160
        blas_sfmin     = 161

    enum blas_norm_type:
        blas_one_norm       = 171
        blas_real_one_norm  = 172
        blas_two_norm       = 173
        blas_frobenius_norm = 174
        blas_inf_norm       = 175
        blas_real_inf_norm  = 176
        blas_max_norm       = 177
        blas_real_max_norm  = 178

    enum blas_sort_type:
        blas_increasing_order = 181
        blas_decreasing_order = 182

    enum blas_conj_type:
        blas_conj    = 191
        blas_no_conj = 192

    enum blas_jrot_type:
        blas_jrot_inner  = 201
        blas_jrot_outer  = 202
        blas_jrot_sorted = 203

    enum blas_prec_type:
        blas_prec_single     = 211
        blas_prec_double     = 212
        blas_prec_indigenous = 213
        blas_prec_extra      = 214

    enum blas_base_type:
        blas_zero_base = 221
        blas_one_base  = 222

    enum blas_symmetry_type:
        blas_general          = 231
        blas_symmetric        = 232
        blas_hermitian        = 233
        blas_triangular       = 234
        blas_lower_triangular = 235
        blas_upper_triangular = 236
        blas_lower_symmetric  = 237
        blas_upper_symmetric  = 238
        blas_lower_hermitian  = 239
        blas_upper_hermitian  = 240

    enum blas_field_type:
        blas_complex          = 241
        blas_real             = 242
        blas_double_precision = 243
        blas_single_precision = 244

    enum blas_size_type:
        blas_num_rows      = 251
        blas_num_cols      = 252
        blas_num_nonzeros  = 253

    enum blas_handle_type:
        blas_invalid_handle = 261
        blas_new_handle     = 262
        blas_open_handle    = 263
        blas_valid_handle   = 264

    enum blas_sparsity_optimization_type:
        blas_regular       = 271
        blas_irregular     = 272
        blas_block         = 273
        blas_unassembled   = 274


    ctypedef int blas_sparse_matrix

    ### Level 1 Computational Routines

    cdef void BLAS_susdot( blas_conj_type conj, int nz, const float *x,
                      const int *indx, const float *y, int incy, float *r,
                      blas_base_type index_base )
    cdef void BLAS_dusdot( blas_conj_type conj, int nz, const double *x,
                      const int *indx, const double *y, int incy, double *r,
                      blas_base_type index_base )
    cdef void BLAS_cusdot( blas_conj_type conj, int nz, const void *x,
                      const int *indx, const void *y, int incy, void *r,
                      blas_base_type index_base )
    cdef void BLAS_zusdot( blas_conj_type conj, int nz, const void *x,
                      const int *indx, const void *y, int incy, void *r,
                      blas_base_type index_base )

    cdef void BLAS_susaxpy( int nz, float alpha, const float *x, const int *indx,
                     float *y, int incy, blas_base_type index_base )
    cdef void BLAS_dusaxpy( int nz, double alpha, const double *x, const int *indx,
                     double *y, int incy, blas_base_type index_base )
    cdef void BLAS_cusaxpy( int nz, const void *alpha, const void *x, const int *indx,
                     void *y, int incy, blas_base_type index_base )
    cdef void BLAS_zusaxpy( int nz, const void *alpha, const void *x, const int *indx,
                     void *y, int incy, blas_base_type index_base )

    cdef void BLAS_susga( int nz, const float *y, int incy, float *x, const int *indx,
                  blas_base_type index_base )
    cdef void BLAS_dusga( int nz, const double *y, int incy, double *x, const int *indx,
                  blas_base_type index_base )
    cdef void BLAS_cusga( int nz, const void *y, int incy, void *x, const int *indx,
                  blas_base_type index_base )
    cdef void BLAS_zusga( int nz, const void *y, int incy, void *x, const int *indx,
                  blas_base_type index_base )

    cdef void BLAS_susgz( int nz, float *y, int incy, float *x, const int *indx,
                  blas_base_type index_base )
    cdef void BLAS_dusgz( int nz, double *y, int incy, double *x, const int *indx,
                   blas_base_type index_base )
    cdef void BLAS_cusgz( int nz, void *y, int incy, void *x, const int *indx,
                   blas_base_type index_base )
    cdef void BLAS_zusgz( int nz, void *y, int incy, void *x, const int *indx,
                   blas_base_type index_base )

    cdef void BLAS_sussc( int nz, const float *x, float *y, int incy, const int *indx,
                   blas_base_type index_base )
    cdef void BLAS_dussc( int nz, const double *x, double *y, int incy, const int *indx,
                   blas_base_type index_base )
    cdef void BLAS_cussc( int nz, const void *x, void *y, int incy, const int *indx,
                   blas_base_type index_base )
    cdef void BLAS_zussc( int nz, const void *x, void *y, int incy, const int *indx,
                   blas_base_type index_base )

    ### Level 2 Computational Routines

    cdef int BLAS_susmv(  blas_trans_type transa, float alpha,
        blas_sparse_matrix A, const float *x, int incx, float *y, int incy )
    cdef int BLAS_dusmv(  blas_trans_type transa, double alpha,
        blas_sparse_matrix A, const double *x, int incx, double *y, int incy )
    cdef int BLAS_cusmv(  blas_trans_type transa, const void *alpha,
        blas_sparse_matrix A, const void *x, int incx, void *y, int incy )
    cdef int BLAS_zusmv(  blas_trans_type transa, const void *alpha,
        blas_sparse_matrix A, const void *x, int incx, void *y, int incy )

    cdef int BLAS_sussv(  blas_trans_type transt, float alpha,
        blas_sparse_matrix T, float *x, int incx )
    cdef int BLAS_dussv(  blas_trans_type transt, double alpha,
        blas_sparse_matrix T, double *x, int incx )
    cdef int BLAS_cussv(  blas_trans_type transt, const void *alpha,
        blas_sparse_matrix T, void *x, int incx )
    cdef int BLAS_zussv(  blas_trans_type transt, const void *alpha,
        blas_sparse_matrix T, void *x, int incx )

    ### Level 3 Computational Routines

    cdef int BLAS_susmm(  blas_order_type order,  blas_trans_type transa,
        int nrhs, float alpha, blas_sparse_matrix A, const float *b, int ldb,
            float *c, int ldc )
    cdef int BLAS_dusmm(  blas_order_type order,  blas_trans_type transa,
            int nrhs, double alpha, blas_sparse_matrix A, const double *b,
            int ldb, double *c, int ldc )
    cdef int BLAS_cusmm(  blas_order_type order,  blas_trans_type transa,
             int nrhs, const void *alpha, blas_sparse_matrix A, const void *b,
         int ldb, void *c, int ldc )
    cdef int BLAS_zusmm(  blas_order_type order,  blas_trans_type transa,
             int nrhs, const void *alpha, blas_sparse_matrix A, const void *b,
         int ldb, void *c, int ldc )

    cdef int BLAS_sussm(  blas_order_type order,  blas_trans_type transt,
                  int nrhs, float alpha, int t, float *b, int ldb )
    cdef int BLAS_dussm(  blas_order_type order,  blas_trans_type transt,
                  int nrhs, double alpha, int t, double *b, int ldb )
    cdef int BLAS_cussm(  blas_order_type order,  blas_trans_type transt,
                  int nrhs, const void *alpha, int t, void *b, int ldb )
    cdef int BLAS_zussm(  blas_order_type order,  blas_trans_type transt,
                  int nrhs, const void *alpha, int t, void *b, int ldb )

    ### Handle Management Routines

    ### Creation Routines

    cdef blas_sparse_matrix BLAS_suscr_begin( int m, int n )
    cdef blas_sparse_matrix BLAS_duscr_begin( int m, int n )
    cdef blas_sparse_matrix BLAS_cuscr_begin( int m, int n )
    cdef blas_sparse_matrix BLAS_zuscr_begin( int m, int n )


    cdef blas_sparse_matrix BLAS_suscr_block_begin( int Mb, int Nb, int k, int l )
    cdef blas_sparse_matrix BLAS_duscr_block_begin( int Mb, int Nb, int k, int l )
    cdef blas_sparse_matrix BLAS_cuscr_block_begin( int Mb, int Nb, int k, int l )
    cdef blas_sparse_matrix BLAS_zuscr_block_begin( int Mb, int Nb, int k, int l )

    cdef blas_sparse_matrix BLAS_suscr_variable_block_begin( int Mb, int Nb,
                    const int *k, const int *l )
    cdef blas_sparse_matrix BLAS_duscr_variable_block_begin( int Mb, int Nb,
                    const int *k, const int *l )
    cdef blas_sparse_matrix BLAS_cuscr_variable_block_begin( int Mb, int Nb,
                    const int *k, const int *l )
    cdef blas_sparse_matrix BLAS_zuscr_variable_block_begin( int Mb, int Nb,
                    const int *k, const int *l )


    ### Insertion Routines

    cdef int BLAS_suscr_insert_entry( blas_sparse_matrix A, float val, int i, int j )
    cdef int BLAS_duscr_insert_entry( blas_sparse_matrix A, double val, int i, int j )
    cdef int BLAS_cuscr_insert_entry( blas_sparse_matrix A, const void *val, int i, int j )
    cdef int BLAS_zuscr_insert_entry( blas_sparse_matrix A, const void *val, int i, int j )

    cdef int BLAS_suscr_insert_entries( blas_sparse_matrix A, int nz, const float *val,
                                const int *indx, const int *jndx )
    cdef int BLAS_duscr_insert_entries( blas_sparse_matrix A, int nz, const double *val,
                                const int *indx, const int *jndx )
    cdef int BLAS_cuscr_insert_entries( blas_sparse_matrix A, int nz, const void *val,
                                const int *indx, const int *jndx )
    cdef int BLAS_zuscr_insert_entries( blas_sparse_matrix A, int nz, const void *val,
                                const int *indx, const int *jndx )

    cdef int BLAS_suscr_insert_col( blas_sparse_matrix A, int j, int nz,
                               const float *val, const int *indx )
    cdef int BLAS_duscr_insert_col( blas_sparse_matrix A, int j, int nz,
                               const double *val, const int *indx )
    cdef int BLAS_cuscr_insert_col( blas_sparse_matrix A, int j, int nz,
                               const void *val, const int *indx )
    cdef int BLAS_zuscr_insert_col( blas_sparse_matrix A, int j, int nz,
                               const void *val, const int *indx )

    cdef int BLAS_suscr_insert_row( blas_sparse_matrix A, int i, int nz,
                               const float *val, const int *indx )
    cdef int BLAS_duscr_insert_row( blas_sparse_matrix A, int i, int nz,
                               const double *val, const int *indx )
    cdef int BLAS_cuscr_insert_row( blas_sparse_matrix A, int i, int nz,
                               const void *val, const int *indx )
    cdef int BLAS_zuscr_insert_row( blas_sparse_matrix A, int i, int nz,
                               const void *val, const int *indx )

    cdef int BLAS_suscr_insert_clique( blas_sparse_matrix A, const int k, const int l,
                            const float *val, const int row_stride,
                            const int col_stride, const int *indx,
                            const int *jndx )
    cdef int BLAS_duscr_insert_clique( blas_sparse_matrix A, const int k, const int l,
                            const double *val, const int row_stride,
                            const int col_stride, const int *indx,
                            const int *jndx )
    cdef int BLAS_cuscr_insert_clique( blas_sparse_matrix A, const int k, const int l,
                            const void *val, const int row_stride,
                            const int col_stride, const int *indx,
                            const int *jndx )
    cdef int BLAS_zuscr_insert_clique( blas_sparse_matrix A, const int k, const int l,
                            const void *val, const int row_stride,
                            const int col_stride, const int *indx,
                            const int *jndx )

    cdef int BLAS_suscr_insert_block( blas_sparse_matrix A, const float *val,
                            int row_stride, int col_stride, int i, int j )
    cdef int BLAS_duscr_insert_block( blas_sparse_matrix A, const double *val,
                            int row_stride, int col_stride, int i, int j )
    cdef int BLAS_cuscr_insert_block( blas_sparse_matrix A, const void *val,
                            int row_stride, int col_stride, int i, int j )
    cdef int BLAS_zuscr_insert_block( blas_sparse_matrix A, const void *val,
                            int row_stride, int col_stride, int i, int j )

    ### Completion of Construction Routines

    cdef int BLAS_suscr_end( blas_sparse_matrix A )
    cdef int BLAS_duscr_end( blas_sparse_matrix A )
    cdef int BLAS_cuscr_end( blas_sparse_matrix A )
    cdef int BLAS_zuscr_end( blas_sparse_matrix A )

    ### Matrix Property Routines

    cdef int BLAS_usgp( blas_sparse_matrix A, int pname )
    cdef int BLAS_ussp( blas_sparse_matrix A, int pname )

    ### Destruction Routine

    cdef int BLAS_usds( blas_sparse_matrix A )
