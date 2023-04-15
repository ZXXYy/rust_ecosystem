# export CVE_ID=""
# export HASH=""
export FULL_ANALYSIS_DIR=$4
export RUSTC="/home/xiaoyez/rust_vulnerabilities/source_analysis/unsafeAnalysis/target/release/rustc"
export SYSROOT="$(rustc --print sysroot)"
export LD_LIBRARY_PATH="$SYSROOT/lib"
export RUSTFLAGS="--cap-lints warn"
# export RUSTFLAGS="$RUSTFLAGS -A dead_code -A warnings -A unused_must_use" 
if [ ! -d $FULL_ANALYSIS_DIR ]; then
  mkdir -p $FULL_ANALYSIS_DIR
fi

cd $1
RUSTFLAGS="$RUSTFLAGS -A dead_code -A warnings -A unused_must_use" cargo build
# check if build success or not
if [ $? -ne 0 ]; then
    failed=1
else 
    failed=0
fi
cargo clean
if [ $failed -ne 1 ]; then
    exit 0
else
    exit 1
fi


