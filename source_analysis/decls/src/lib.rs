pub mod blocks;
pub mod functions;
pub mod items;
pub mod unsafe_imports;
pub mod implicit;

use std::fs::DirBuilder;
use std::fs::File;
use std::fs::OpenOptions;
use std::path::PathBuf;
use std::time::SystemTime;
use std::fmt::Write;
use serde::{Serialize, Deserialize};

pub static BLOCKS_IN_FUNCTIONS: &'static str = "02_blocks_in_function";
pub static FUNCTIONS: &'static str = "01_functions";

pub static BLOCK_SUMMARY_BB: &'static str = "01_blocks_summary";
pub static BLOCK_UNSAFETY_SOURCES_FILE_NAME: &'static str = "01_unsafe_blocks_sources";


pub static SUMMARY_FUNCTIONS_FILE_NAME: &'static str = "02_summary_functions";
pub static SUMMARY_FUNCTIONS_RESTRICTED: &'static str = "02_summary_restricted";
pub static FN_UNSAFETY_SOURCES_FILE_NAME: &'static str = "02_unsafe_fn_sources";

pub static UNSAFE_TRAITS: &'static str = "02_unsafe_traits";
pub static UNSAFE_TRAITS_IMPLS: &'static str = "03_unsafe_traits_impls";

pub static IMPLICIT_RTA_OPTIMISTIC_FILENAME: &'static str = "11_precise_opt_unsafe_in_call_tree";
pub static IMPLICIT_RTA_PESSIMISTIC_FILENAME: &'static str = "11_precise_pes_unsafe_in_call_tree";

pub static RESTRICTED_RTA_OPTIMISTIC_FILENAME: &'static str = "12_restricted_opt_unsafe_in_call_tree";
pub static RESTRICTED_RTA_PESSIMISTIC_FILENAME: &'static str = "12_restricted_pes_unsafe_in_call_tree";

#[derive(Serialize, Deserialize, Debug)]
pub enum Abi {
    Cdecl,
    Stdcall,
    Fastcall,
    Vectorcall,
    Thiscall,
    Aapcs,
    Win64,
    SysV64,
    PtxKernel,
    Msp430Interrupt,
    X86Interrupt,
    AmdGpuKernel,
    Rust,
    C,
    System,
    RustIntrinsic,
    RustCall,
    PlatformIntrinsic,
    Unadjusted,
    EfiApi,
    AvrInterrupt,
    AvrNonBlockingInterrupt,
    CCmseNonSecureCall,
    Wasm,
}

pub struct FileOps<'a,'b> {
    crate_name: &'a String,
    crate_version: &'a String,
    commit_hash: &'a String,
    root_dir: &'b String
}

impl<'a, 'b> FileOps<'a, 'b> {
    pub fn new(crate_name: &'a String, crate_version: &'a String, commit_hash: &'a String, root_dir: &'b String) -> Self {
        FileOps {
            crate_name,
            crate_version,
            commit_hash,
            root_dir,
        }
    }

    pub fn create_file(&self, analysis_name: &'static str) -> File {
        let mut filename = String::new();
        filename.push_str(analysis_name);
        if let Err(e) = write!(filename, "_{:?}", SystemTime::now().duration_since(SystemTime::UNIX_EPOCH).unwrap().as_nanos()){
            println!("Writing error: {}", e.to_string()); 
        }

//        print!("Saving {:?}", filename);

        let file_path = self.get_path(filename);
        // create new file
        OpenOptions::new()
            .read(true)
            .write(true)
            .create(true)
            .truncate(true) // if true overwrites the old file
            .open(file_path)
            .unwrap()
    }

    fn get_path(&self, filename: String) -> PathBuf {
        // create directory if necessary
        let dir_path: PathBuf = self.get_root_path_components().iter().collect();
        DirBuilder::new().recursive(true).create(dir_path).unwrap();

        let file_path: PathBuf = self.get_analysis_path_components(filename).iter().collect();
        file_path
    }

    pub fn get_root_path_components(&self) -> [String; 4] {
        [
            self.root_dir.to_string(),
            self.crate_name.clone(),
            self.crate_version.clone(),
            self.commit_hash.clone(),
        ]
    }

    pub fn get_analysis_path_components(&self, filename: String) -> [String; 5] {
        [
            self.root_dir.to_string(),
            self.crate_name.clone(),
            self.crate_version.clone(),
            self.commit_hash.clone(),
            filename,
        ]
    }

    pub fn open_files(&self, analysis_name: &'static str) -> Option<Vec<File>> {
        let dir_path: PathBuf = self.get_root_path_components().iter().collect();
        //error!("Using dir {:?}", dir_path);
        if let Ok(read_dir) = dir_path.read_dir() {
            let mut result = Vec::new();
            for entry in read_dir {
                // check if entry is ./analysis_name_*
                if let Some(filename) = entry.unwrap().path().as_path().file_name() {
                    //error!("Found file {:?}", filename.to_str());
                    if filename.to_str().unwrap().to_string().starts_with(analysis_name) {
                        let file_path = dir_path.join(filename);
                        // create new file
                        result.push(OpenOptions::new()
                            .read(true)
                            .create(false)
                            .open(file_path)
                            .unwrap());
                    }
                }
            }
            Some (result)
        } else {
            None
        }

    }

    pub fn get_max_version(dir_path: &PathBuf) -> String {
        if let Ok(dir_entries) = std::fs::read_dir(dir_path) {
            let version = dir_entries.filter_map(
                |dir_result| {
                    if let Ok(dd) = dir_result {
                        let pb = &dd.path();
                        if let Some(name) = pb.file_name() {
                            Some(name.to_os_string())
                        } else {
                            None
                        }
                    } else {
                        None
                    }
                }
            ).max();
            if let Some(version) = version {
                version.to_str().unwrap().to_string()
            } else {
                assert!(false, "Can't find version in dir {:?}", dir_path);
                "".to_string()
            }
        } else {
            assert!(false, "Can't read_dir {:?}", dir_path);
            "".to_string()
        }
    }

}