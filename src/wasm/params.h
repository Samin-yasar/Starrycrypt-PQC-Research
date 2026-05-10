#ifndef PQCLEAN_MLKEM768_CLEAN_PARAMS_H
#define PQCLEAN_MLKEM768_CLEAN_PARAMS_H

/*
 * NOTE: KYBER_* macros below are PQClean reference-library internal names.
 * The external API (api.h) uses PQCLEAN_MLKEM768_CLEAN_* per FIPS 203.
 * With KYBER_K=3 these parameters produce the finalized ML-KEM-768
 * byte sizes: pk=1184, ct=1088, sk=2400, ss=32.
 */


/* Don't change parameters below this line */

#define KYBER_N 256
#define KYBER_Q 3329

#define KYBER_SYMBYTES 32   /* size in bytes of hashes, and seeds */
#define KYBER_SSBYTES  32   /* size in bytes of shared key */

#define KYBER_POLYBYTES     384
#define KYBER_POLYVECBYTES  (KYBER_K * KYBER_POLYBYTES)

#define KYBER_K 3
#define KYBER_ETA1 2
#define KYBER_POLYCOMPRESSEDBYTES    128
#define KYBER_POLYVECCOMPRESSEDBYTES (KYBER_K * 320)

#define KYBER_ETA2 2

#define KYBER_INDCPA_MSGBYTES       (KYBER_SYMBYTES)
#define KYBER_INDCPA_PUBLICKEYBYTES (KYBER_POLYVECBYTES + KYBER_SYMBYTES)
#define KYBER_INDCPA_SECRETKEYBYTES (KYBER_POLYVECBYTES)
#define KYBER_INDCPA_BYTES          (KYBER_POLYVECCOMPRESSEDBYTES + KYBER_POLYCOMPRESSEDBYTES)

#define KYBER_PUBLICKEYBYTES  (KYBER_INDCPA_PUBLICKEYBYTES)
/* 32 bytes of additional space to save H(pk) */
#define KYBER_SECRETKEYBYTES  (KYBER_INDCPA_SECRETKEYBYTES + KYBER_INDCPA_PUBLICKEYBYTES + 2*KYBER_SYMBYTES)
#define KYBER_CIPHERTEXTBYTES (KYBER_INDCPA_BYTES)

#endif
