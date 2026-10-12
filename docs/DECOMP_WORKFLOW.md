# What a real decompilation does

1. **Fix the target.** Identify the game revision and keep hashes of the original inputs. Base and update code must not be silently mixed.
2. **Map the executable.** Separate containers, code, data, and modules. Recover load addresses, instruction modes, and relocations before interpreting references.
3. **Decode and trace.** Turn instruction bytes into assembly, establish function/control-flow boundaries, and follow calls and data references. Tables can resemble instructions, so independent decoding matters.
4. **Recover meaning.** Determine what each function does and infer argument types, structures, state, ownership, and side effects. Export symbols can restore some original names; most inferred details still need evidence.
5. **Write source.** Reconstruct maintainable C/C++ that implements the observed behavior. Decompiler pseudocode is a starting point, not finished source.
6. **Compile and compare.** First prove an unchanged-binary reconstruction. Then compile reconstructed functions with an appropriate toolchain and compare instructions, relocations, and data. Exact matching and behavior-tested nonmatching implementations are different statuses.
7. **Integrate and test.** Verify that compiled source replacements were actually selected in the build, then test the affected behavior in the rebuilt game. Booting while still retaining original sections does not establish source reconstruction progress.
8. **Port separately if desired.** A native PC version also needs host implementations for required console graphics, input, audio, storage, and OS services. A matching 3DS build does not automatically provide those.

Our project has proved the analysis path for the main executable and one locally relocated module. Compiler identification, unchanged-binary rebuild, source replacement, and runtime verification remain ahead.
